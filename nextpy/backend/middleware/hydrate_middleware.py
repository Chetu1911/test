"""Middleware to hydrate the state."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nextpy import constants
from nextpy.backend.event import Event, get_hydrate_event
from nextpy.backend.middleware.middleware import Middleware
from nextpy.backend.state import BaseState, StateUpdate
from nextpy.utils import format

if TYPE_CHECKING:
    from nextpy.app import App


class HydrateMiddleware(Middleware):
    """Middleware to handle initial app hydration."""

    async def preprocess(
        self, app: App, state: BaseState, event: Event
    ) -> Optional[StateUpdate]:
        """Preprocess the event.

        Args:
            app: The app to apply the middleware to.
            state: The client state.
            event: The event to preprocess.

        Returns:
            An optional delta or list of state updates to return.
        """
        # If this is not the hydrate event, return None
        if event.name != get_hydrate_event(state):
            return None

        # Clear client storage, to respect clearing cookies
        state._reset_client_storage()

        # Mark state as not hydrated (until on_loads are complete)
        setattr(state, constants.CompileVars.IS_HYDRATED, False)

        # Apply client side storage values to state
        for storage_type in (constants.COOKIES, constants.LOCAL_STORAGE):
            if storage_type in event.payload:
                for key, value in event.payload[storage_type].items():
                    state_name, _, var_name = key.rpartition(".")
                    var_state = state.get_substate(state_name.split("."))
                    setattr(var_state, var_name, value)

        # Get the initial state.
        delta = format.format_state(state.dict())
        # since a full dict was captured, clean any dirtiness
        state._clean()

        # Return the state update.
        return StateUpdate(delta=delta, events=[])
