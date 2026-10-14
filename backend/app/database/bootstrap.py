from sqlalchemy.orm import Session

from app.models.tables import Account, Instrument

INSTRUMENTS = [
    ("EUR_USD", "oanda", "forex", "0.00001", "1", "1", "0.00030"),
    ("GBP_USD", "oanda", "forex", "0.00001", "1", "1", "0.00040"),
    ("BTC-USD", "coinbase", "crypto", "0.01", "0.00000001", "0.0001", "50"),
    ("ETH-USD", "coinbase", "crypto", "0.01", "0.00000001", "0.001", "5"),
]


def bootstrap(db: Session):
    for values in INSTRUMENTS:
        if not db.get(Instrument, values[0]):
            db.add(
                Instrument(
                    **dict(
                        zip(
                            [
                                "symbol",
                                "provider",
                                "asset_class",
                                "tick_size",
                                "unit_step",
                                "min_units",
                                "max_spread",
                            ],
                            values,
                            strict=True,
                        )
                    )
                )
            )
    if not db.get(Account, "PAPER"):
        db.add(Account(id="PAPER"))
    db.commit()
