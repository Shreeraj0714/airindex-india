from ..collectors.demo_collector import ROUTE_BASKET

PROTOTYPE_WEIGHT_LABEL = "Prototype configurable weights — not official CPI weights."


def route_weights() -> dict[str, float]:
    return dict(ROUTE_BASKET)
