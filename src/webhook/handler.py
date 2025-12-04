"""
Webhook request handler.
"""
from typing import Optional, Callable, Awaitable
from fastapi import Request, HTTPException, status

from .models import PushEvent, GitProvider
from .parser import WebhookParserFactory


class WebhookHandler:
    """Handles incoming webhook requests."""
    
    def __init__(self):
        self._event_callbacks: list[Callable[[PushEvent], Awaitable[None]]] = []
    
    def on_push_event(self, callback: Callable[[PushEvent], Awaitable[None]]):
        """Register callback for push events."""
        self._event_callbacks.append(callback)
    
    async def handle_webhook(
        self,
        request: Request,
        provider: GitProvider,
        secret: Optional[str] = None
    ) -> dict:
        """
        Handle incoming webhook request.
        
        Args:
            request: FastAPI request object
            provider: Git provider type
            secret: Optional webhook secret for verification
            
        Returns:
            Response dict
            
        Raises:
            HTTPException: If verification fails or parsing fails
        """
        # Read raw body for signature verification
        body = await request.body()
        
        # Get signature from headers
        signature = self._get_signature_header(request, provider)
        
        # Create parser
        parser = WebhookParserFactory.create(provider)
        
        # Verify signature if secret is provided
        if secret and signature:
            if not parser.verify_signature(body, signature, secret):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature"
                )
        
        # Parse payload
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Parse into unified event
        event = parser.parse(payload)
        
        if not event:
            # Not a push event or parsing failed
            return {"status": "ignored", "reason": "not a push event"}
        
        # Filter: only process main branch
        if not event.is_main_branch:
            return {
                "status": "ignored",
                "reason": f"not main branch (got: {event.branch})"
            }
        
        # Trigger callbacks
        for callback in self._event_callbacks:
            try:
                await callback(event)
            except Exception as e:
                # Log error but don't fail the webhook
                print(f"Error in callback: {e}")
        
        return {
            "status": "success",
            "event": {
                "provider": event.provider,
                "repository": event.repository_name,
                "branch": event.branch,
                "commit": event.commit_sha[:7]
            }
        }
    
    def _get_signature_header(self, request: Request, provider: GitProvider) -> Optional[str]:
        """Extract signature header based on provider."""
        header_map = {
            GitProvider.GITEA: "X-Gitea-Signature",
            GitProvider.GITHUB: "X-Hub-Signature-256",
            GitProvider.GITLAB: "X-Gitlab-Token",
        }
        
        header_name = header_map.get(provider)
        if not header_name:
            return None
        
        return request.headers.get(header_name)
