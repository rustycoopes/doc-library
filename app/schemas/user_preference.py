from typing import Literal

from pydantic import BaseModel


class ViewModePreference(BaseModel):
    view_mode: Literal["list", "tiles"]
