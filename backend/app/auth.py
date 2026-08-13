"""
Role-Based Access Control (demo-grade, matching the rest of this project's
'simple, explainable, honestly-labeled' approach to auth).

The frontend sends the signed-in user's role in an X-User-Role header on
every request (see src/lib/auth.ts + src/lib/backend-api.ts). This module
is what actually ENFORCES it server-side -- hiding a button in the UI is
not access control, since anyone can still hit the API directly. Missing
or unrecognized roles are treated as the lowest privilege level (Viewer),
never trusted upward, so a request with no role header can't accidentally
get elevated access.

Same stated limitation as auth.ty: this is a header-based demo, not a real
signed session/token. A production version would derive the role from a
verified session (e.g. JWT issued at login by an identity provider), not
from a client-supplied header the caller could set to whatever they want.
That's still a real gap worth stating -- but it's a different problem from
"does the app enforce roles at all", which this does fix.
"""

from fastapi import Header, Depends, HTTPException

ROLE_LEVELS = {
    "Viewer": 0,             # read-only: dashboard, exceptions, suppliers, reports
    "Procurement Manager": 1,  # + approve/reject exceptions, add notes, trigger pipeline runs
    "Admin": 2,               # + manage suppliers, upload/delete/reindex knowledge base docs
}


def get_current_role(x_user_role: str = Header(default="Viewer")) -> str:
    """Reads the caller's role from the X-User-Role header. Unknown or
    missing values fall back to 'Viewer' (least privilege), never higher."""
    return x_user_role if x_user_role in ROLE_LEVELS else "Viewer"


def require_role(min_role: str):
    """
    FastAPI dependency factory: require_role("Admin") blocks the request
    with a 403 unless the caller's role is Admin (or, for other minimums,
    at least that level in the Viewer < Procurement Manager < Admin order).
    """
    min_level = ROLE_LEVELS[min_role]

    def dependency(role: str = Depends(get_current_role)) -> str:
        if ROLE_LEVELS[role] < min_level:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires the '{min_role}' role or higher "
                       f"(you are signed in as '{role}').",
            )
        return role

    return dependency
