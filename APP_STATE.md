# App State & Implementation Details

## Overview
Modular Market Intelligence Terminal using a plugin-based architecture.

## Directory Structure (Current)
- `bbt10/`: Main active directory.
- `app_modular.py`: Main entry point.
- `architecture_modular.py`: Plugin registry and base classes.
- `upstox_fo_complete.py`: Core logic for Upstox F&O data fetching and Greek calculations.
- `preprocess_nse_data.py`: Utility to filter `NSE.json` into `instrument_master.json`.

## Current State of Features
| Feature | Status | Notes |
|---------|--------|-------|
| Price Data (yfinance) | ✅ Working | Standard OHLCV fetching. Handles Midcap 100 correctly. |
| Options Analysis | ✅ Improved | Works for Indices and now captures Stock F&O via improved `preprocess_nse_data.py`. |
| Greeks Analysis | ✅ Improved | Uses dynamic `key_map` to handle delimiter variations (`|` vs `:`). |
| Futures Analysis | ✅ Improved | Basis calculation more robust with key discovery. |
| Fundamentals | ✅ Working | Scrapes screener.in. |
| AI Insights | 🚧 Pending | Button exists, logic needs verification. |

## Implementation Details: Dynamic Key Mapping
The `UpstoxFOData` class now includes a `key_map` dictionary. When an API call succeeds via fallback scanning (finding a key with `last_price` that doesn't match the requested key exactly), the original key is mapped to the discovered key. This prevents repeated slow fallback scans.

## Upstox API Response Structure (Observed)
- **Market Quote:**
  ```json
  {
    "status": "success",
    "data": {
      "NSE_EQ:ITC": {
        "last_price": 325.8,
        "oi": 0,
        "volume": 12345
      }
    }
  }
  ```
- **Option Chain:**
  ```json
  {
    "status": "success",
    "data": [
      {
        "strike_price": 25000,
        "call_options": { "market_data": { "ltp": 100, "oi": 500 }, "option_greeks": { "delta": 0.5 } },
        "put_options": { "market_data": { "ltp": 80, "oi": 400 }, "option_greeks": { "delta": -0.4 } }
      }
    ]
  }
  ```

## Known Issues (Resolved)
1. **Instrument Mapping:** Fixed in `preprocess_nse_data.py` by matching `asset_symbol` for stock F&O.
2. **KeyError 'CE_OI':** Resolved with empty data checks in `plugins_advanced.py`.
3. **Symbol Mismatch:** `NIFTY_MIDCAP_100.NS` integrated into `app_modular.py`.

## Planned Fixes
1. Update `preprocess_nse_data.py` to use `asset_symbol` for matching stock F&O.
2. Add empty data checks in `plugins_advanced.py` to prevent crashes.
3. Verify `upstox_fo_complete.py` fallback logic for instrument keys.
