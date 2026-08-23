#property strict
#property version   "0.90"
#property description "FTMO US100.cash native-feed V17 14-branch forward candidate"
#property description "No CME/Databento/external market data. Fixed $70 risk on 10k by default."

#include <Trade/Trade.mqh>

#include "US100_V17_Core.mqh"
#include "US100_V17_Features.mqh"
#include "US100_V17_Signals.mqh"
#include "US100_V17_Execution.mqh"
