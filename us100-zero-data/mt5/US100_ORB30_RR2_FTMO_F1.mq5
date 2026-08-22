#property strict
#property version   "1.00"
#property description "FTMO US100.cash native-feed ORB30 RR2 F1 forward candidate"
#property description "No external market data. One trade/day. Fixed intended risk."

#include <Trade/Trade.mqh>

CTrade g_trade;

input double InpRiskDollars       = 30.0;
input double InpRewardRisk        = 2.0;
input ulong  InpMagic             = 260822301;
input int    InpORStartHour       = 16;
input int    InpORStartMinute     = 30;
input int    InpOREndHour         = 17;
input int    InpOREndMinute       = 0;
input int    InpSignalEndHour     = 19;
input int    InpSignalEndMinute   = 0;
input int    InpFlattenHour       = 22;
input int    InpFlattenMinute     = 55;
input bool   InpWriteCommonLog    = true;

string   LOG_FILE = "US100_ORB30_RR2_FTMO_F1.csv";
datetime g_lastM1Open = 0;
int      g_dayKey = -1;
double   g_orHigh = 0.0;
double   g_orLow = 0.0;
int      g_orBars = 0;
bool     g_orReady = false;
bool     g_signalConsumed = false;

int MinuteOfDay(datetime t)
{
   MqlDateTime x;
   TimeToStruct(t, x);
   return x.hour * 60 + x.min;
}

int DayKey(datetime t)
{
   MqlDateTime x;
   TimeToStruct(t, x);
   return x.year * 10000 + x.mon * 100 + x.day;
}

datetime DayTime(datetime ref, int hh, int mm, int ss=0)
{
   MqlDateTime x;
   TimeToStruct(ref, x);
   x.hour = hh;
   x.min = mm;
   x.sec = ss;
   return StructToTime(x);
}

string SignalGVName()
{
   return "ORB30_F1_SIGNAL_" + _Symbol + "_" + (string)InpMagic;
}

int VolumeDigits(double step)
{
   int d = 0;
   while(d < 8 && MathAbs(step - NormalizeDouble(step, d)) > 1e-12)
      d++;
   return d;
}

double NormalizeVolumeDown(double raw)
{
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step <= 0.0 || vmin <= 0.0 || vmax <= 0.0)
      return 0.0;

   double v = MathFloor(raw / step + 1e-10) * step;
   v = MathMin(v, vmax);
   v = NormalizeDouble(v, VolumeDigits(step));
   if(v + 1e-12 < vmin)
      return 0.0;
   return v;
}

void LogEvent(string eventName,
              string direction="",
              double signalClose=0.0,
              double volume=0.0,
              double entryRef=0.0,
              double sl=0.0,
              double tp=0.0,
              string note="")
{
   if(!InpWriteCommonLog)
      return;

   MqlTick tick;
   ZeroMemory(tick);
   SymbolInfoTick(_Symbol, tick);
   double spread = (tick.ask > 0.0 && tick.bid > 0.0) ? tick.ask - tick.bid : 0.0;

   int flags = FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE;
   flags |= FILE_COMMON;
   int h = FileOpen(LOG_FILE, flags, ';');
   if(h == INVALID_HANDLE)
      return;

   if(FileSize(h) == 0)
   {
      FileWrite(h,
                "server_time","event","symbol","bid","ask","spread_price",
                "or_high","or_low","direction","signal_close","risk_dollars",
                "volume","entry_ref","sl","tp","trade_retcode","note");
   }
   FileSeek(h, 0, SEEK_END);
   FileWrite(h,
             TimeToString(TimeTradeServer(), TIME_DATE|TIME_SECONDS),
             eventName,
             _Symbol,
             DoubleToString(tick.bid, _Digits),
             DoubleToString(tick.ask, _Digits),
             DoubleToString(spread, _Digits),
             DoubleToString(g_orHigh, _Digits),
             DoubleToString(g_orLow, _Digits),
             direction,
             DoubleToString(signalClose, _Digits),
             DoubleToString(InpRiskDollars, 2),
             DoubleToString(volume, 4),
             DoubleToString(entryRef, _Digits),
             DoubleToString(sl, _Digits),
             DoubleToString(tp, _Digits),
             (string)g_trade.ResultRetcode(),
             note);
   FileClose(h);
}

bool OwnPosition(ulong &ticketOut)
{
   ticketOut = 0;
   for(int i=PositionsTotal()-1; i>=0; --i)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      ticketOut = ticket;
      return true;
   }
   return false;
}

bool HadEntryDealToday(datetime now)
{
   datetime start = DayTime(now, 0, 0, 0);
   if(!HistorySelect(start, now))
      return false;

   int total = HistoryDealsTotal();
   for(int i=0; i<total; ++i)
   {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0)
         continue;
      if(HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol)
         continue;
      if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagic)
         continue;
      long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_IN || entry == DEAL_ENTRY_INOUT)
         return true;
   }
   return false;
}

bool BuildOpeningRange(datetime now)
{
   g_orHigh = -DBL_MAX;
   g_orLow = DBL_MAX;
   g_orBars = 0;
   g_orReady = false;

   datetime from = DayTime(now, InpORStartHour, InpORStartMinute, 0);
   datetime to = DayTime(now, InpOREndHour, InpOREndMinute, 0) - 1;
   if(now <= from)
      return false;

   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   int n = CopyRates(_Symbol, PERIOD_M1, from, to, rates);
   if(n != 30)
      return false;

   for(int i=0; i<n; ++i)
   {
      datetime expected = from + i * 60;
      if(rates[i].time != expected)
         return false;
      if(rates[i].high > g_orHigh) g_orHigh = rates[i].high;
      if(rates[i].low < g_orLow) g_orLow = rates[i].low;
   }

   g_orBars = n;
   g_orReady = (g_orHigh > g_orLow && g_orBars == 30);
   if(g_orReady)
      LogEvent("OR_READY", "", 0.0, 0.0, 0.0, 0.0, 0.0, "30 contiguous M1 bars");
   return g_orReady;
}

void ResetForDay(datetime now)
{
   g_dayKey = DayKey(now);
   g_orHigh = 0.0;
   g_orLow = 0.0;
   g_orBars = 0;
   g_orReady = false;

   bool gvConsumed = false;
   string gv = SignalGVName();
   if(GlobalVariableCheck(gv))
      gvConsumed = ((int)GlobalVariableGet(gv) == g_dayKey);

   g_signalConsumed = gvConsumed || HadEntryDealToday(now);

   if(MinuteOfDay(now) >= InpOREndHour * 60 + InpOREndMinute)
      BuildOpeningRange(now);

   LogEvent("DAY_RESET", "", 0.0, 0.0, 0.0, 0.0, 0.0,
            g_signalConsumed ? "signal already consumed/traded" : "ready");
}

void ConsumeSignal()
{
   g_signalConsumed = true;
   GlobalVariableSet(SignalGVName(), (double)g_dayKey);
}

bool CalculateVolume(ENUM_ORDER_TYPE type, double entry, double stop, double &volume)
{
   volume = 0.0;
   double oneLotProfit = 0.0;
   if(!OrderCalcProfit(type, _Symbol, 1.0, entry, stop, oneLotProfit))
      return false;
   double lossOneLot = MathAbs(oneLotProfit);
   if(lossOneLot <= 0.0)
      return false;

   double raw = InpRiskDollars / lossOneLot;
   volume = NormalizeVolumeDown(raw);
   return volume > 0.0;
}

bool StopsAreValid(double entry, double stop)
{
   int stopsLevelPts = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist = stopsLevelPts * _Point;
   if(minDist <= 0.0)
      return true;
   return MathAbs(entry - stop) >= minDist;
}

bool ModifyTargetToActualFill(ulong ticket, string direction, double stop)
{
   if(!PositionSelectByTicket(ticket))
      return false;
   double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
   double risk = (direction == "long") ? (openPrice - stop) : (stop - openPrice);
   if(risk <= 0.0)
      return false;
   double tp = (direction == "long") ? openPrice + InpRewardRisk * risk
                                      : openPrice - InpRewardRisk * risk;
   tp = NormalizeDouble(tp, _Digits);
   bool ok = g_trade.PositionModify(ticket, NormalizeDouble(stop, _Digits), tp);
   LogEvent(ok ? "TP_SYNC_OK" : "TP_SYNC_FAIL", direction, 0.0,
            PositionGetDouble(POSITION_VOLUME), openPrice, stop, tp,
            ok ? "TP based on actual fill" : g_trade.ResultRetcodeDescription());
   return ok;
}

void ExecuteSignal(string direction, double signalClose)
{
   ConsumeSignal();  // first valid signal is consumed even if broker rejects the order

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
   {
      LogEvent("ORDER_SKIPPED", direction, signalClose, 0, 0, 0, 0, "no tick");
      return;
   }

   double entryRef = (direction == "long") ? tick.ask : tick.bid;
   double stop = (direction == "long") ? g_orLow : g_orHigh;
   if(entryRef <= 0.0 || stop <= 0.0)
   {
      LogEvent("ORDER_SKIPPED", direction, signalClose, 0, entryRef, stop, 0, "invalid prices");
      return;
   }

   double riskDist = (direction == "long") ? (entryRef - stop) : (stop - entryRef);
   if(riskDist <= 0.0)
   {
      LogEvent("ORDER_SKIPPED", direction, signalClose, 0, entryRef, stop, 0, "entry beyond opposite OR edge");
      return;
   }
   if(!StopsAreValid(entryRef, stop))
   {
      LogEvent("ORDER_SKIPPED", direction, signalClose, 0, entryRef, stop, 0, "broker minimum stop distance");
      return;
   }

   ENUM_ORDER_TYPE type = (direction == "long") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double volume = 0.0;
   if(!CalculateVolume(type, entryRef, stop, volume))
   {
      LogEvent("ORDER_SKIPPED", direction, signalClose, 0, entryRef, stop, 0, "volume below minimum or calc failure");
      return;
   }

   stop = NormalizeDouble(stop, _Digits);
   double tpRef = (direction == "long") ? entryRef + InpRewardRisk * riskDist
                                         : entryRef - InpRewardRisk * riskDist;
   tpRef = NormalizeDouble(tpRef, _Digits);

   LogEvent("SIGNAL", direction, signalClose, volume, entryRef, stop, tpRef, "first breakout of day");

   bool sent = false;
   if(direction == "long")
      sent = g_trade.Buy(volume, _Symbol, 0.0, stop, 0.0, "ORB30_RR2_F1");
   else
      sent = g_trade.Sell(volume, _Symbol, 0.0, stop, 0.0, "ORB30_RR2_F1");

   if(!sent)
   {
      LogEvent("ORDER_REJECTED", direction, signalClose, volume, entryRef, stop, 0,
               g_trade.ResultRetcodeDescription());
      return;
   }

   ulong ticket = 0;
   if(OwnPosition(ticket))
   {
      PositionSelectByTicket(ticket);
      double actualOpen = PositionGetDouble(POSITION_PRICE_OPEN);
      LogEvent("ORDER_FILLED", direction, signalClose,
               PositionGetDouble(POSITION_VOLUME), actualOpen, stop, 0,
               g_trade.ResultRetcodeDescription());
      ModifyTargetToActualFill(ticket, direction, stop);
   }
   else
   {
      LogEvent("ORDER_SENT_NO_POSITION_FOUND", direction, signalClose, volume, entryRef, stop, 0,
               g_trade.ResultRetcodeDescription());
   }
}

void FlattenIfDue(datetime now)
{
   int flattenMin = InpFlattenHour * 60 + InpFlattenMinute;
   if(MinuteOfDay(now) < flattenMin)
      return;

   ulong ticket = 0;
   if(!OwnPosition(ticket))
      return;

   if(g_trade.PositionClose(ticket))
      LogEvent("FORCED_FLATTEN", "", 0, 0, 0, 0, 0, "22:55 platform time");
   else
      LogEvent("FLATTEN_FAIL", "", 0, 0, 0, 0, 0, g_trade.ResultRetcodeDescription());
}

int OnInit()
{
   if(_Period != PERIOD_M1)
      Print("ORB30 F1: attach/run on M1. Current chart period is ", EnumToString((ENUM_TIMEFRAMES)_Period));

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetAsyncMode(false);

   datetime now = TimeTradeServer();
   g_lastM1Open = iTime(_Symbol, PERIOD_M1, 0);
   ResetForDay(now);
   LogEvent("EA_INIT", "", 0, 0, 0, 0, 0, "F1 frozen defaults");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   LogEvent("EA_DEINIT", "", 0, 0, 0, 0, 0, "reason=" + (string)reason);
}

void OnTick()
{
   datetime now = TimeTradeServer();
   if(DayKey(now) != g_dayKey)
      ResetForDay(now);

   FlattenIfDue(now);

   datetime curBarOpen = iTime(_Symbol, PERIOD_M1, 0);
   if(curBarOpen <= 0 || curBarOpen == g_lastM1Open)
      return;
   g_lastM1Open = curBarOpen;

   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, PERIOD_M1, 0, 2, r) < 2)
      return;
   MqlRates closed = r[1];
   int m = MinuteOfDay(closed.time);

   int orStart = InpORStartHour * 60 + InpORStartMinute;
   int orEnd = InpOREndHour * 60 + InpOREndMinute;
   int signalEnd = InpSignalEndHour * 60 + InpSignalEndMinute;

   if(m >= orStart && m < orEnd)
   {
      if(g_orBars == 0)
      {
         g_orHigh = closed.high;
         g_orLow = closed.low;
      }
      else
      {
         if(closed.high > g_orHigh) g_orHigh = closed.high;
         if(closed.low < g_orLow) g_orLow = closed.low;
      }
      g_orBars++;
      if(g_orBars == 30)
      {
         g_orReady = (g_orHigh > g_orLow);
         if(g_orReady)
            LogEvent("OR_READY", "", 0, 0, 0, 0, 0, "built live from 30 bars");
      }
      return;
   }

   if(m < orEnd || m >= signalEnd || g_signalConsumed)
      return;

   if(!g_orReady && !BuildOpeningRange(now))
   {
      LogEvent("SIGNAL_SCAN_SKIPPED", "", closed.close, 0, 0, 0, 0, "OR incomplete");
      return;
   }

   ulong ownTicket = 0;
   if(OwnPosition(ownTicket))
      return;

   if(closed.close > g_orHigh)
      ExecuteSignal("long", closed.close);
   else if(closed.close < g_orLow)
      ExecuteSignal("short", closed.close);
}

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || trans.deal == 0)
      return;
   ulong deal = trans.deal;
   if(HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol)
      return;
   if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagic)
      return;

   long entryType = HistoryDealGetInteger(deal, DEAL_ENTRY);
   double price = HistoryDealGetDouble(deal, DEAL_PRICE);
   double profit = HistoryDealGetDouble(deal, DEAL_PROFIT);
   double commission = HistoryDealGetDouble(deal, DEAL_COMMISSION);
   double swap = HistoryDealGetDouble(deal, DEAL_SWAP);
   double volume = HistoryDealGetDouble(deal, DEAL_VOLUME);
   string note = "deal=" + (string)deal +
                 " profit=" + DoubleToString(profit,2) +
                 " commission=" + DoubleToString(commission,2) +
                 " swap=" + DoubleToString(swap,2);

   if(entryType == DEAL_ENTRY_IN || entryType == DEAL_ENTRY_INOUT)
      LogEvent("DEAL_IN", "", 0, volume, price, 0, 0, note);
   else if(entryType == DEAL_ENTRY_OUT || entryType == DEAL_ENTRY_OUT_BY)
      LogEvent("DEAL_OUT", "", 0, volume, price, 0, 0, note);
}
