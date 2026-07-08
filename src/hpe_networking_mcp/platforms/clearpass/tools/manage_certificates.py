"""ClearPass certificate management write tools."""

from __future__ import annotations

from typing import Annotated

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import Field

from hpe_networking_mcp.middleware.elicitation import confirm_write
from hpe_networking_mcp.platforms.clearpass._registry import tool
from hpe_networking_mcp.platforms.clearpass.client import get_clearpass_session
from hpe_networking_mcp.platforms.clearpass.tools import WRITE_DELETE

_CERT_ACTIONS = (
    "import_trust_list",
    "delete_trust_list",
    "delete_client_cert",
    "enable_server_cert",
    "disable_server_cert",
    "install_server_cert",
)



async def _confirm_write(ctx: Context, action: str, identifier: str | None) -> dict | None:
    """Thin wrapper over :func:`middleware.elicitation.confirm_write`.

    Kept as a local helper so existing call sites don't change; the
    shared elicitation/decline/cancel logic now lives in the middleware
    (#148).
    """
    label = identifier or "unknown"
    return await confirm_write(ctx, f"ClearPass: {action} certificate '{label}'. Confirm?")


@tool(annotations=WRITE_DELETE, tags={"clearpass_write_delete"})
async def clearpass_manage_certificate(
    ctx: Context,
    action_type: Annotated[
        str,
        Field(
            description="Action: 'import_trust_list', 'delete_trust_list', 'delete_client_cert', "
            "'enable_server_cert', 'disable_server_cert', or 'install_server_cert'."
        ),
    ],
    payload: Annotated[
        dict,
        Field(
            description="Certificate payload. For import_trust_list: {'cert_file': '<PEM string>', "
            "'cert_usage': ['Others', ...]}. For install_server_cert: {'certificate_url': '<url>'} or "
            "{'pkcs12_file_url': '<url>', 'pkcs12_passphrase': '<pass>'} — ClearPass fetches the cert by "
            "URL; inline PEM content ('cert_file') is NOT accepted for this action (verified against a "
            "live server — see install_server_cert docs below). For delete/enable/disable: empty dict {}."
        ),
    ],
    cert_id: Annotated[
        str | None,
        Field(description="Certificate ID (required for delete_trust_list, delete_client_cert)."),
    ] = None,
    server_uuid: Annotated[
        str | None,
        Field(description="Server UUID (required for enable/disable_server_cert and install_server_cert)."),
    ] = None,
    service_name: Annotated[
        str | None,
        Field(
            description="Service name, one of 'RADIUS', 'HTTPS(ECC)', 'HTTPS(RSA)', 'RadSec', 'Database'. "
            "Required for enable/disable_server_cert and install_server_cert."
        ),
    ] = None,
    confirmed: Annotated[bool, Field(description="Set true after user confirms the operation.")] = False,
) -> dict | str:
    """Manage ClearPass certificates (trust lists, client certs, server certs).

    Actions:
        import_trust_list: Import a CA certificate into the trust list. Payload requires cert_file
            (PEM string) and cert_usage (list of usage strings, e.g. ['Others']).
        delete_trust_list: Remove a CA certificate from the trust list by cert_id.
        delete_client_cert: Remove a client certificate by cert_id.
        enable_server_cert: Enable a server certificate for a service (requires server_uuid and service_name).
        disable_server_cert: Disable a server certificate for a service (requires server_uuid and service_name).
        install_server_cert: Install a CA-signed certificate for a server-cert slot (requires server_uuid
            and service_name). Calls PUT /server-cert/name/{server_uuid}/{service_name} — verified against
            a live ClearPass 6.14 server that this endpoint ONLY accepts 'certificate_url' or
            'pkcs12_file_url'+'pkcs12_passphrase' in the payload; it rejects inline 'cert_file' PEM content
            with "Invalid post body. Either provide certificate_url or pkcs12_file_url and
            pkcs12_passphrase." The signed cert (or PKCS12 bundle) must be hosted at a URL ClearPass can
            fetch. Pairs with clearpass_create_csr's guidance to generate the CSR via the Admin UI first.

    Args:
        action_type: Certificate operation to perform.
        payload: Certificate data for import. Empty dict for other actions.
        cert_id: Certificate ID. Required for delete_trust_list and delete_client_cert.
        server_uuid: Server UUID. Required for enable/disable_server_cert and install_server_cert.
        service_name: Service name. Required for enable/disable_server_cert and install_server_cert.
        confirmed: Set true after user confirms. Skips re-prompting.
    """
    if action_type not in _CERT_ACTIONS:
        raise ToolError(
            {
                "status_code": 400,
                "message": f"Invalid action_type '{action_type}'. Must be one of: {', '.join(_CERT_ACTIONS)}.",
            }
        )

    if not confirmed:
        identifier = cert_id or server_uuid or "certificate"
        decline = await _confirm_write(ctx, action_type.replace("_", " "), identifier)
        if decline:
            return decline

    try:
        from pyclearpass.api_certificateauthority import ApiCertificateAuthority

        client = await get_clearpass_session(ApiCertificateAuthority)
        return _execute_cert_action(client, action_type, payload, cert_id, server_uuid, service_name)
    except ToolError:
        raise
    except Exception as e:
        raise ToolError({"status_code": 502, "message": f"Error managing certificate: {e}"}) from e


def _execute_cert_action(
    client,
    action_type: str,
    payload: dict,
    cert_id: str | None,
    server_uuid: str | None,
    service_name: str | None,
) -> dict | str:
    """Execute the resolved certificate action.

    Args:
        client: pyclearpass ApiCertificateAuthority instance.
        action_type: Certificate operation to perform.
        payload: Certificate data payload.
        cert_id: Certificate ID for delete operations.
        server_uuid: Server UUID for enable/disable operations.
        service_name: Service name for enable/disable operations.

    Returns:
        API response dict or error string.
    """
    if action_type == "import_trust_list":
        return client._send_request("/cert-trust-list", "post", query=payload)

    if action_type == "delete_trust_list":
        if not cert_id:
            raise ToolError({"status_code": 400, "message": "cert_id is required for delete_trust_list."})
        return client.delete_cert_trust_list_by_cert_trust_list_id(cert_trust_list_id=cert_id)

    if action_type == "delete_client_cert":
        if not cert_id:
            raise ToolError({"status_code": 400, "message": "cert_id is required for delete_client_cert."})
        return client.delete_client_cert_by_client_cert_id(client_cert_id=cert_id)

    if action_type in ("enable_server_cert", "disable_server_cert"):
        if not server_uuid or not service_name:
            raise ToolError(
                {
                    "status_code": 400,
                    "message": "server_uuid and service_name are required for enable/disable_server_cert.",
                }
            )
        action = "enable" if action_type == "enable_server_cert" else "disable"
        path = f"/server-cert/name/{server_uuid}/{service_name}/{action}"
        return client._send_request(path, "patch", query={})

    if action_type == "install_server_cert":
        if not server_uuid or not service_name:
            raise ToolError(
                {
                    "status_code": 400,
                    "message": "server_uuid and service_name are required for install_server_cert.",
                }
            )
        if not payload.get("certificate_url") and not payload.get("pkcs12_file_url"):
            raise ToolError(
                {
                    "status_code": 400,
                    "message": "payload must include 'certificate_url', or 'pkcs12_file_url' + "
                    "'pkcs12_passphrase' — this ClearPass endpoint does not accept inline 'cert_file' "
                    "PEM content; the cert must be hosted at a URL ClearPass can fetch.",
                }
            )
        path = f"/server-cert/name/{server_uuid}/{service_name}"
        return client._send_request(path, "put", query=payload)

    raise ToolError({"status_code": 500, "message": f"Unhandled action_type: {action_type}"})


@tool(annotations=WRITE_DELETE, tags={"clearpass_write_delete"})
async def clearpass_create_csr(
    ctx: Context,
    payload: Annotated[
        dict,
        Field(
            description="Unused — kept for backward compatibility. See the raised error for why."
        ),
    ] = {},  # noqa: B006 — intentionally unused, tool always errors
    confirmed: Annotated[bool, Field(description="Unused — kept for backward compatibility.")] = False,
) -> dict | str:
    """Always raises — CSR generation has no REST API endpoint in ClearPass.

    Verified against a live server: ``POST /certificate/csr`` returns 405
    (``Allow: GET, DELETE`` only), and ``GET /certificate/csr`` returns 422
    ("ID 'csr' is invalid") — proving ``/certificate/csr`` is not a real
    endpoint but the generic ``/certificate/{id}`` route misparsing the
    literal string "csr" as a certificate ID. There is no documented
    ``pyclearpass`` method for CSR generation either.

    ClearPass only supports generating a server-certificate CSR through the
    Admin Web UI (Administration > Certificates > Certificate Store >
    Server Certificates tab > Create Certificate Signing Request) — this
    keeps the private key on the appliance, which the REST API has no way
    to do. Generate the CSR there, get it signed externally, then install
    the signed cert with ``clearpass_manage_certificate``
    (``action_type="install_server_cert"``).
    """
    raise ToolError(
        {
            "status_code": 501,
            "message": (
                "ClearPass has no REST API for CSR generation — generate it via the Admin UI "
                "(Administration > Certificates > Certificate Store > Server Certificates tab > "
                "Create Certificate Signing Request), get it signed, then install the signed cert "
                "with clearpass_manage_certificate(action_type='install_server_cert')."
            ),
        }
    )
