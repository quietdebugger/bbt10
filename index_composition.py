"""
Index Composition Data for Portfolio X-Ray
Contains constituent weights and ETF mappings.
Weights are approximate based on recent Free Float Market Cap data (as of 2025/2026).
"""

# ETF Symbol -> Underlying Index ID
ETF_MAPPING = {
    # Nifty 50 ETFs
    'NIFTYBEES': 'NIFTY_50',
    'SETFNIF50': 'NIFTY_50',
    'ICICINIFTY': 'NIFTY_50',
    'KOTAKNIFTY': 'NIFTY_50',
    'HDFCNIFTY': 'NIFTY_50',
    'UTINIFTETF': 'NIFTY_50',
    'NIFTYIETF': 'NIFTY_50', # SBI Nifty 50 ETF
    'SBIETF': 'NIFTY_50',
    
    # Bank Nifty ETFs
    'BANKBEES': 'NIFTY_BANK',
    'SETFBANK': 'NIFTY_BANK',
    'KOTAKBKETF': 'NIFTY_BANK',
    'ICICIBANKP': 'NIFTY_BANK',
    'HDFCBANKETF': 'NIFTY_BANK',
    'SBIBANKETF': 'NIFTY_BANK',
    
    # Sector/Thematic ETFs
    'AUTOBEES': 'NIFTY_AUTO',
    'NETFAUTO': 'NIFTY_AUTO',
    'ITBEES': 'NIFTY_IT',
    'SETFNN50': 'NIFTY_NEXT_50',
    'PHARMABEES': 'NIFTY_PHARMA',
    'PSUBNKBEES': 'NIFTY_PSU_BANK',
    'INFRAIETF': 'NIFTY_INFRA',
    'COMMODITIES': 'NIFTY_COMMODITIES', # Hypothetical
    'CPSEETF': 'NIFTY_CPSE',
    'MNCETF': 'NIFTY_MNC', # Hypothetical
    
    # Strategy
    'NV20BEES': 'NIFTY_NV20',
    'ICICINV20': 'NIFTY_NV20',
    'MID150BEES': 'NIFTY_MIDCAP_150',
}

# Index ID -> {Stock Symbol: Weight % (0-100)}
# Updated with 2025/2026 data
INDEX_WEIGHTS = {
    'NIFTY_50': {
        'RELIANCE.NS': 9.54, 'HDFCBANK.NS': 6.85, 'BHARTIARTL.NS': 5.89, 'SBIN.NS': 5.24,
        'TCS.NS': 5.05, 'ICICIBANK.NS': 4.83, 'INFY.NS': 4.50, 'ITC.NS': 3.80,
        'LT.NS': 3.50, 'AXISBANK.NS': 2.90, 'BAJFINANCE.NS': 2.89, 'KOTAKBANK.NS': 2.50,
        'HINDUNILVR.NS': 2.20, 'MARUTI.NS': 1.80, 'SUNPHARMA.NS': 1.70, 'M&M.NS': 1.60,
        'TITAN.NS': 1.50, 'ULTRACEMCO.NS': 1.40, 'TATASTEEL.NS': 1.30, 'NTPC.NS': 1.25,
        'POWERGRID.NS': 1.20, 'TATAMOTORS.NS': 1.15, 'ADANIENT.NS': 1.10, 'ONGC.NS': 1.05,
        'JSWSTEEL.NS': 1.00, 'HCLTECH.NS': 0.95, 'COALINDIA.NS': 0.90, 'GRASIM.NS': 0.85,
        'NESTLEIND.NS': 0.80, 'BAJAJ-AUTO.NS': 0.75, 'ADANIPORTS.NS': 0.70, 'DRREDDY.NS': 0.65,
        'CIPLA.NS': 0.60, 'WIPRO.NS': 0.55, 'TECHM.NS': 0.50, 'HINDALCO.NS': 0.45,
        'BPCL.NS': 0.40, 'EICHERMOT.NS': 0.35, 'BRITANNIA.NS': 0.30, 'APOLLOHOSP.NS': 0.30,
        'TATACONSUM.NS': 0.25, 'DIVISLAB.NS': 0.25, 'SBILIFE.NS': 0.20, 'HDFCLIFE.NS': 0.20,
        'INDUSINDBK.NS': 0.80 # Kept from previous if still valid
    },
    'NIFTY_BANK': {
        'HDFCBANK.NS': 28.17, 'ICICIBANK.NS': 25.23, 'SBIN.NS': 8.72, 'AXISBANK.NS': 8.40,
        'KOTAKBANK.NS': 8.36, 'INDUSINDBK.NS': 3.72, 'FEDERALBNK.NS': 3.38, 'IDFCFIRSTB.NS': 3.11,
        'BANKBARODA.NS': 2.98, 'AUBANK.NS': 2.97, 'PNB.NS': 2.50, 'BANDHANBNK.NS': 1.50
    },
    'NIFTY_IT': {
        'INFY.NS': 29.32, 'TCS.NS': 21.68, 'HCLTECH.NS': 10.61, 'TECHM.NS': 9.53,
        'WIPRO.NS': 7.22, 'PERSISTENT.NS': 6.18, 'LTIM.NS': 5.22, 'COFORGE.NS': 5.21,
        'MPHASIS.NS': 2.96, 'OFSS.NS': 1.74
    },
    'NIFTY_AUTO': {
        'MARUTI.NS': 19.35, 'M&M.NS': 18.56, 'TATAMOTORS.NS': 11.86, 'BAJAJ-AUTO.NS': 11.09,
        'EICHERMOT.NS': 8.13, 'TVSMOTOR.NS': 7.26, 'HEROMOTOCO.NS': 5.00, 'BHARATFORG.NS': 4.50,
        'ASHOKLEY.NS': 4.00, 'TIINDIA.NS': 3.00, 'MRF.NS': 3.00, 'BALKRISIND.NS': 2.50,
        'SONACOMS.NS': 1.50, 'BOSCHLTD.NS': 1.50, 'EXIDEIND.NS': 1.00
    },
    'NIFTY_PHARMA': {
        'SUNPHARMA.NS': 21.30, 'CIPLA.NS': 11.43, 'DIVISLAB.NS': 9.96, 'DRREDDY.NS': 9.81,
        'LUPIN.NS': 6.58, 'TORNTPHARM.NS': 5.22, 'LAURUSLAB.NS': 4.73, 'AUROPHARMA.NS': 4.26,
        'ALKEM.NS': 4.19, 'GLENMARK.NS': 3.83, 'BIOCON.NS': 4.00, 'ZYDUSLIFE.NS': 4.00
    },
    'NIFTY_FMCG': {
        'HINDUNILVR.NS': 25.38, 'ITC.NS': 17.49, 'NESTLEIND.NS': 11.04, 'VBL.NS': 6.78,
        'BRITANNIA.NS': 6.36, 'GODREJCP.NS': 5.42, 'TATACONSUM.NS': 5.00, 'DABUR.NS': 5.00,
        'MARICO.NS': 4.00, 'COLPAL.NS': 3.00
    },
    'NIFTY_METAL': {
        'TATASTEEL.NS': 19.61, 'JSWSTEEL.NS': 14.94, 'HINDALCO.NS': 14.85, 'ADANIENT.NS': 13.02,
        'VEDL.NS': 12.35, 'HINDZINC.NS': 11.98, 'JINDALSTEL.NS': 7.00, 'NMDC.NS': 5.00,
        'SAIL.NS': 5.00, 'COALINDIA.NS': 5.00
    },
    'NIFTY_REALTY': {
        'DLF.NS': 22.90, 'LODHA.NS': 14.60, 'GODREJPROP.NS': 14.48, 'PHOENIXLTD.NS': 12.35,
        'PRESTIGE.NS': 12.02, 'OBEROIRLTY.NS': 10.08, 'BRIGADE.NS': 7.09, 'SOBHA.NS': 5.00
    },
    'NIFTY_ENERGY': {
        'RELIANCE.NS': 33.42, 'NTPC.NS': 6.01, 'ONGC.NS': 5.81, 'ADANIPOWER.NS': 4.89,
        'POWERGRID.NS': 4.61, 'BPCL.NS': 4.00, 'IOC.NS': 4.00, 'GAIL.NS': 3.00,
        'COALINDIA.NS': 3.00, 'TATASTEEL.NS': 2.00 # Placeholder if needed
    },
    'NIFTY_PSU_BANK': {
        'SBIN.NS': 52.12, 'BANKBARODA.NS': 7.41, 'PNB.NS': 6.97, 'UNIONBANK.NS': 6.75,
        'CANBK.NS': 6.57, 'INDIANB.NS': 6.00, 'BANKINDIA.NS': 5.00
    },
    'NIFTY_INFRA': {
        'RELIANCE.NS': 23.86, 'BHARTIARTL.NS': 14.73, 'LT.NS': 6.89, 'ULTRACEMCO.NS': 4.47,
        'NTPC.NS': 4.28, 'BEL.NS': 4.87, 'POWERGRID.NS': 4.00, 'ONGC.NS': 3.00
    },
    'NIFTY_COMMODITIES': {
        'RELIANCE.NS': 28.53, 'ULTRACEMCO.NS': 5.49, 'NTPC.NS': 5.13, 'ONGC.NS': 4.96,
        'JSWSTEEL.NS': 4.38, 'TATASTEEL.NS': 4.00, 'HINDALCO.NS': 3.50, 'COALINDIA.NS': 3.00
    },
    'NIFTY_CPSE': {
        'BEL.NS': 20.90, 'NTPC.NS': 20.37, 'POWERGRID.NS': 16.59, 'ONGC.NS': 14.92,
        'COALINDIA.NS': 14.29, 'OIL.NS': 5.00, 'NHPC.NS': 5.00
    },
    'NIFTY_PSE': {
        'NTPC.NS': 13.52, 'BEL.NS': 12.89, 'POWERGRID.NS': 9.31, 'ONGC.NS': 8.37,
        'COALINDIA.NS': 8.02, 'SBIN.NS': 7.00, 'GAIL.NS': 5.00, 'BPCL.NS': 5.00
    },
    'NIFTY_MNC': {
        'HINDUNILVR.NS': 17.70, 'MARUTI.NS': 14.83, 'VEDL.NS': 8.38, 'NESTLEIND.NS': 7.70,
        'BRITANNIA.NS': 4.43, 'COLPAL.NS': 4.00, 'ABB.NS': 4.00, 'SIEMENS.NS': 4.00,
        'CUMMINSIND.NS': 3.00, 'HONAUT.NS': 2.00
    },
    'NIFTY_NV20': {
        'ITC.NS': 15.0, 'RELIANCE.NS': 14.0, 'TCS.NS': 13.0, 'INFY.NS': 12.0,
        'HCLTECH.NS': 9.0, 'HINDUNILVR.NS': 8.0, 'LT.NS': 7.0, 'SUNPHARMA.NS': 5.0,
        'WIPRO.NS': 4.0, 'GRASIM.NS': 3.0, 'TECHM.NS': 3.0, 'HINDALCO.NS': 2.0,
        'JSWSTEEL.NS': 2.0, 'CIPLA.NS': 1.0, 'DRREDDY.NS': 1.0, 'HEROMOTOCO.NS': 1.0
    }
}

# Sector mapping for top stocks
STOCK_SECTORS = {
    'HDFCBANK.NS': 'Financials', 'RELIANCE.NS': 'Energy', 'ICICIBANK.NS': 'Financials',
    'INFY.NS': 'Technology', 'ITC.NS': 'FMCG', 'TCS.NS': 'Technology', 'LT.NS': 'Construction',
    'AXISBANK.NS': 'Financials', 'KOTAKBANK.NS': 'Financials', 'HINDUNILVR.NS': 'FMCG',
    'SBIN.NS': 'Financials', 'BHARTIARTL.NS': 'Telecom', 'BAJFINANCE.NS': 'Financials',
    'ASIANPAINT.NS': 'Consumer', 'MARUTI.NS': 'Auto', 'TITAN.NS': 'Consumer',
    'SUNPHARMA.NS': 'Healthcare', 'M&M.NS': 'Auto', 'NTPC.NS': 'Utilities',
    'ULTRACEMCO.NS': 'Materials', 'TATAMOTORS.NS': 'Auto', 'POWERGRID.NS': 'Utilities',
    'TATASTEEL.NS': 'Materials', 'JSWSTEEL.NS': 'Materials', 'ADANIENT.NS': 'Diversified',
    'HCLTECH.NS': 'Technology', 'ONGC.NS': 'Energy', 'NESTLEIND.NS': 'FMCG',
    'INDUSINDBK.NS': 'Financials', 'GRASIM.NS': 'Materials', 'ADANIPORTS.NS': 'Infrastructure',
    'BAJAJ-AUTO.NS': 'Auto', 'DRREDDY.NS': 'Healthcare', 'CIPLA.NS': 'Healthcare',
    'COALINDIA.NS': 'Energy', 'WIPRO.NS': 'Technology', 'SBILIFE.NS': 'Financials',
    'HDFCLIFE.NS': 'Financials', 'TECHM.NS': 'Technology', 'BPCL.NS': 'Energy',
    'BRITANNIA.NS': 'FMCG', 'EICHERMOT.NS': 'Auto', 'HINDALCO.NS': 'Materials',
    'TATACONSUM.NS': 'FMCG', 'APOLLOHOSP.NS': 'Healthcare', 'DIVISLAB.NS': 'Healthcare',
    'HEROMOTOCO.NS': 'Auto', 'UPL.NS': 'Materials', 'BANKBARODA.NS': 'Financials',
    'PNB.NS': 'Financials', 'IDFCFIRSTB.NS': 'Financials', 'AUBANK.NS': 'Financials',
    'FEDERALBNK.NS': 'Financials', 'TVSMOTOR.NS': 'Auto', 'BHARATFORG.NS': 'Auto Anc',
    'ASHOKLEY.NS': 'Auto', 'TIINDIA.NS': 'Auto Anc', 'MRF.NS': 'Auto Anc',
    'BALKRISIND.NS': 'Auto Anc', 'SONACOMS.NS': 'Auto Anc', 'BOSCHLTD.NS': 'Auto Anc',
    'EXIDEIND.NS': 'Auto Anc', 'LTIM.NS': 'Technology', 'PERSISTENT.NS': 'Technology',
    'COFORGE.NS': 'Technology', 'MPHASIS.NS': 'Technology', 'OFSS.NS': 'Technology',
    # New additions for thematic coverage
    'DLF.NS': 'Realty', 'GODREJPROP.NS': 'Realty', 'PHOENIXLTD.NS': 'Realty', 'OBEROIRLTY.NS': 'Realty',
    'LODHA.NS': 'Realty', 'PRESTIGE.NS': 'Realty', 'BRIGADE.NS': 'Realty', 'SOBHA.NS': 'Realty',
    'JINDALSTEL.NS': 'Metals', 'NMDC.NS': 'Metals', 'SAIL.NS': 'Metals', 'VEDL.NS': 'Metals',
    'HINDZINC.NS': 'Metals',
    'ADANIGREEN.NS': 'Energy', 'GAIL.NS': 'Energy', 'IOC.NS': 'Energy', 'ADANIPOWER.NS': 'Energy',
    'BEL.NS': 'Defence', 'HAL.NS': 'Defence', 'COLPAL.NS': 'FMCG', 'DABUR.NS': 'FMCG', 'MARICO.NS': 'FMCG',
    'VBL.NS': 'FMCG', 'LUPIN.NS': 'Healthcare', 'TORNTPHARM.NS': 'Healthcare', 'ALKEM.NS': 'Healthcare',
    'AUROPHARMA.NS': 'Healthcare', 'BIOCON.NS': 'Healthcare', 'ZYDUSLIFE.NS': 'Healthcare',
    'LAURUSLAB.NS': 'Healthcare', 'GLENMARK.NS': 'Healthcare',
    'UNIONBANK.NS': 'Financials', 'INDIANB.NS': 'Financials', 'BANKINDIA.NS': 'Financials',
    'BANDHANBNK.NS': 'Financials',
    'ABB.NS': 'Capital Goods', 'SIEMENS.NS': 'Capital Goods', 'CUMMINSIND.NS': 'Capital Goods',
    'HONAUT.NS': 'Capital Goods',
    'NHPC.NS': 'Utilities', 'OIL.NS': 'Energy'
}
