from datetime import datetime, timezone

from src.api_client import query_documents
from src.config import Config
from src.validator import validate_request


def process_requests(
    requests: list[dict[str, str]],
    config: Config,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    for request in requests:
        request_id = (request.get("request_id") or "").strip()
        errors = validate_request(request)

        if errors:
            results.append(
                {
                    "request_id": request_id,
                    "status": "invalid",
                    "http_status": None,
                    "attempts": 0,
                    "message": "; ".join(errors),
                    "document_count": None,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            continue

        api_result = query_documents(
            request=request,
            base_url=config.api_base_url,
            token=config.api_token,
            timeout=config.request_timeout,
            max_attempts=config.max_attempts,
        )
        results.append(
            {
                "request_id": request_id,
                **api_result,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return results
