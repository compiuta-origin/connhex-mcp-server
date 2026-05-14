from pydantic import BaseModel


class ConnhexBaseModel(BaseModel):
    # extra="allow" lets API responses pass through unknown fields without
    # breaking validation when Connhex adds new properties in future releases.
    model_config = {"extra": "allow"}
