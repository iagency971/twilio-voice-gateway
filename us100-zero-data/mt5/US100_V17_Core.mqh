CTrade g_trade;

input double InpRiskDollars          = 70.0;   // V17/V19: 0.70% of a 10k starting balance
input ulong  InpMagic                = 260823170;
input int    InpServerToNYHours      = 7;      // frozen research mapping: server time = New York + 7h
input int    InpFeatureBars          = 1600;   // closed M1 bars rebuilt on each new bar
input int    InpDailyLookbackDays    = 420;    // M5 history for RTH daily context / EMA20/EMA50
input double InpDailyWinCapR         = 2.0;    // frozen engine_v2 daily win cap
input bool   InpAllowTrading         = true;   // false = signal/log shadow only
input bool   InpWriteCommonLog       = true;
input double InpMaxRiskOvershootPct  = 2.0;    // post-fill safety: close if actual SL risk exceeds intended risk by >2%

const double MODEL_TICK = 0.25;
const double ATR_STOP_FACTOR = 0.80;
const int    GLOBAL_MIN_RISK_TICKS = 40;
const int    GLOBAL_MAX_RISK_TICKS = 80;

string LOG_FILE = "US100_V17_14BRANCH_FTMO_F1.csv";
datetime g_lastClosedBar = 0;
int g_consecLosses = 0;

struct RiskProfile
{
   double minTicks;
   double maxTicks;
   double minRR;
   double beTrigger;
   double partialRR;
   double trailPct;
   int    timeStopMin;
   int    maxDaily;
   int    priority;
};

struct Signal
{
   int      idx;
   datetime serverTime;
   datetime nyTime;
   string   model;
   string   direction;
   string   tag;
   double   entry;
   double   stop;
   double   target;
   double   riskTicks;
   double   rewardTicks;
   double   rr;
   RiskProfile rp;
};

struct DailyContext
{
   bool   ready;
   double pdh;
   double pdl;
   double prevClose;
   int    regime; // -1 bear, 0 chop, +1 bull
   int    previousDayKey;
};

struct DayAgg
{
   int key;
   double high;
   double low;
   double close;
   int count;
};

struct PositionState
{
   bool active;
   long direction; // +1 long, -1 short
   double entry;
   double baseStop;
   double target;
   double risk;
   double riskDollars;
   double mfe;
   double trailStop;
   bool be;
   bool trailing;
   double beTrigger;
   double partialRR;
   double trailPct;
   int timeStopMin;
   datetime entryTime;
   string model;
};

PositionState g_ps;

// ---------- time / numeric helpers ----------

datetime NYTime(datetime serverTime)
{
   return serverTime - InpServerToNYHours * 3600;
}

int DayKey(datetime t)
{
   MqlDateTime x;
   TimeToStruct(t, x);
   return x.year * 10000 + x.mon * 100 + x.day;
}

int MinuteOfDay(datetime t)
{
   MqlDateTime x;
   TimeToStruct(t, x);
   return x.hour * 60 + x.min;
}

int PyWeekday(datetime t)
{
   MqlDateTime x;
   TimeToStruct(t, x);
   return (x.day_of_week + 6) % 7; // Monday=0 ... Sunday=6
}

int HourOf(datetime t)
{
   MqlDateTime x;
   TimeToStruct(t, x);
   return x.hour;
}

datetime NYDayStartServer(datetime serverNow)
{
   datetime ny = NYTime(serverNow);
   MqlDateTime x;
   TimeToStruct(ny, x);
   x.hour=0; x.min=0; x.sec=0;
   return StructToTime(x) + InpServerToNYHours * 3600;
}

bool ValidD(double x)
{
   return x != EMPTY_VALUE && MathIsValidNumber(x);
}

double LogicalRound(double p)
{
   return MathRound(p / MODEL_TICK) * MODEL_TICK;
}

int VolumeDigits(double step)
{
   int d=0;
   while(d<8 && MathAbs(step-NormalizeDouble(step,d))>1e-12) d++;
   return d;
}

double NormalizeVolumeDown(double raw)
{
   double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(vmin<=0 || vmax<=0 || step<=0) return 0.0;
   double v=MathFloor(raw/step+1e-10)*step;
   v=MathMin(v,vmax);
   v=NormalizeDouble(v,VolumeDigits(step));
   if(v+1e-12<vmin) return 0.0;
   return v;
}

double BrokerTickSize()
{
   double t=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   return (t>0 ? t : _Point);
}

double BrokerPriceNearest(double p)
{
   double t=BrokerTickSize();
   return NormalizeDouble(MathRound(p/t)*t,_Digits);
}

double BrokerStopOutward(long dir,double p)
{
   double t=BrokerTickSize();
   double q=(dir>0 ? MathFloor(p/t+1e-10)*t : MathCeil(p/t-1e-10)*t);
   return NormalizeDouble(q,_Digits);
}

void SortRatesAscending(MqlRates &r[])
{
   int n=ArraySize(r);
   if(n<2 || r[0].time<=r[n-1].time) return;
   for(int i=0;i<n/2;i++)
   {
      MqlRates tmp=r[i];
      r[i]=r[n-1-i];
      r[n-1-i]=tmp;
   }
}

// ---------- logging ----------

void LogEvent(string eventName,string model="",string direction="",double volume=0.0,
              double signalEntry=0.0,double stop=0.0,double target=0.0,string note="")
{
   if(!InpWriteCommonLog) return;
   MqlTick tick; ZeroMemory(tick); SymbolInfoTick(_Symbol,tick);
   int flags=FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_COMMON;
   int h=FileOpen(LOG_FILE,flags,';');
   if(h==INVALID_HANDLE) return;
   if(FileSize(h)==0)
   {
      FileWrite(h,"server_time","ny_time","event","symbol","model","direction","bid","ask","spread",
                   "risk_dollars","volume","signal_entry","stop","target","retcode","note");
   }
   FileSeek(h,0,SEEK_END);
   datetime st=TimeTradeServer();
   FileWrite(h,TimeToString(st,TIME_DATE|TIME_SECONDS),TimeToString(NYTime(st),TIME_DATE|TIME_SECONDS),
             eventName,_Symbol,model,direction,
             DoubleToString(tick.bid,_Digits),DoubleToString(tick.ask,_Digits),
             DoubleToString((tick.ask>0&&tick.bid>0)?tick.ask-tick.bid:0.0,_Digits),
             DoubleToString(InpRiskDollars,2),DoubleToString(volume,4),
             DoubleToString(signalEntry,_Digits),DoubleToString(stop,_Digits),DoubleToString(target,_Digits),
             (string)g_trade.ResultRetcode(),note);
   FileClose(h);
}

// ---------- profiles / branches ----------

bool GetProfile(string model,RiskProfile &rp)
{
   rp.minTicks=40; rp.maxTicks=80; rp.minRR=2.0; rp.beTrigger=0.6; rp.partialRR=0.5;
   rp.trailPct=0.001; rp.timeStopMin=35; rp.maxDaily=1; rp.priority=50;
   if(model=="ema_rev")      {rp.maxTicks=60; rp.minRR=1.3; rp.timeStopMin=35; rp.maxDaily=1; rp.priority=30; return true;}
   if(model=="kalman_mom")   {rp.maxTicks=50; rp.minRR=1.5; rp.timeStopMin=40; rp.maxDaily=1; rp.priority=40; return true;}
   if(model=="open_drive")   {rp.maxTicks=60; rp.minRR=1.5; rp.beTrigger=0.5; rp.timeStopMin=30; rp.maxDaily=2; rp.priority=12; return true;}
   if(model=="ou_lunch")     {rp.maxTicks=60; rp.minRR=1.5; rp.beTrigger=0.5; rp.timeStopMin=25; rp.maxDaily=3; rp.priority=16; return true;}
   if(model=="ou_rev")       {rp.maxTicks=100;rp.minRR=1.5; rp.timeStopMin=35; rp.maxDaily=6; rp.priority=15; rp.trailPct=0.0015; return true;}
   if(model=="pd_rev")       {rp.maxTicks=60; rp.minRR=1.5; rp.timeStopMin=35; rp.maxDaily=1; rp.priority=22; return true;}
   if(model=="pm_mom")       {rp.maxTicks=80; rp.minRR=1.5; rp.timeStopMin=30; rp.maxDaily=1; rp.priority=50; return true;}
   if(model=="sweep")        {rp.maxTicks=80; rp.minRR=2.0; rp.timeStopMin=30; rp.maxDaily=2; rp.priority=35; return true;}
   if(model=="trend")        {rp.maxTicks=120;rp.minRR=2.0; rp.timeStopMin=45; rp.maxDaily=5; rp.priority=40; return true;}
   if(model=="vwap_rev")     {rp.maxTicks=50; rp.minRR=1.3; rp.timeStopMin=40; rp.maxDaily=2; rp.priority=25; return true;}
   if(model=="vwap_scalp")   {rp.maxTicks=50; rp.minRR=1.3; rp.beTrigger=0.5; rp.partialRR=0.4; rp.timeStopMin=20; rp.maxDaily=3; rp.priority=25; return true;}
   return false;
}

int ModelId(string model)
{
   if(model=="ema_rev") return 1;
   if(model=="kalman_mom") return 2;
   if(model=="open_drive") return 3;
   if(model=="ou_lunch") return 4;
   if(model=="ou_rev") return 5;
   if(model=="pd_rev") return 6;
   if(model=="pm_mom") return 7;
   if(model=="sweep") return 8;
   if(model=="trend") return 9;
   if(model=="vwap_rev") return 10;
   if(model=="vwap_scalp") return 11;
   return 0;
}

string ModelName(int id)
{
   if(id==1) return "ema_rev";
   if(id==2) return "kalman_mom";
   if(id==3) return "open_drive";
   if(id==4) return "ou_lunch";
   if(id==5) return "ou_rev";
   if(id==6) return "pd_rev";
   if(id==7) return "pm_mom";
   if(id==8) return "sweep";
   if(id==9) return "trend";
   if(id==10) return "vwap_rev";
   if(id==11) return "vwap_scalp";
   return "";
}

bool BranchSelected(string model,string dir)
{
   if(model=="ema_rev")    return dir=="long";
   if(model=="kalman_mom") return dir=="long" || dir=="short";
   if(model=="open_drive") return dir=="long";
   if(model=="ou_lunch")   return dir=="long" || dir=="short";
   if(model=="ou_rev")     return dir=="long";
   if(model=="pd_rev")     return dir=="long";
   if(model=="pm_mom")     return dir=="long" || dir=="short";
   if(model=="sweep")      return dir=="short";
   if(model=="trend")      return dir=="long";
   if(model=="vwap_rev")   return dir=="short";
   if(model=="vwap_scalp") return dir=="long";
   return false;
}

bool RawRiskOK(double risk,double reward,const RiskProfile &rp)
{
   if(risk<=0) return false;
   double ticks=risk/MODEL_TICK;
   double floorTicks=MathMax(rp.minTicks,(double)GLOBAL_MIN_RISK_TICKS);
   double ceilTicks=MathMin(rp.maxTicks,(double)GLOBAL_MAX_RISK_TICKS);
   if(ticks<floorTicks-1e-9 || ticks>ceilTicks+1e-9) return false;
   return reward/risk>=rp.minRR-1e-12;
}

void MakeSignal(int idx,datetime serverTime,string model,string dir,string tag,
                double rawEntry,double rawStop,double rawTarget,const RiskProfile &rp,Signal &s)
{
   double risk=MathAbs(rawEntry-rawStop);
   double reward=MathAbs(rawTarget-rawEntry);
   s.idx=idx; s.serverTime=serverTime; s.nyTime=NYTime(serverTime);
   s.model=model; s.direction=dir; s.tag=tag;
   s.entry=LogicalRound(rawEntry); s.stop=LogicalRound(rawStop); s.target=LogicalRound(rawTarget);
   s.riskTicks=risk/MODEL_TICK; s.rewardTicks=reward/MODEL_TICK;
   s.rr=(risk>0?reward/risk:0.0); s.rp=rp;
}

bool ApplyATRHybrid(Signal &s,double atr)
{
   if(!ValidD(atr) || atr<=0) return true;
   double atrDist=atr*ATR_STOP_FACTOR;
   double modelDist=MathAbs(s.entry-s.stop);
   if(atrDist<=modelDist) return true;
   double ns=(s.direction=="long" ? s.entry-atrDist : s.entry+atrDist);
   ns=LogicalRound(ns);
   double nr=MathAbs(s.entry-ns);
   double nt=nr/MODEL_TICK;
   if(nt<GLOBAL_MIN_RISK_TICKS-1e-9) return true;
   if(nt>s.rp.maxTicks+1e-9) return true;
   double reward=MathAbs(s.target-s.entry);
   double rr=(nr>0?reward/nr:0.0);
   if(rr<s.rp.minRR-1e-12) return false;
   s.stop=ns; s.riskTicks=nt; s.rewardTicks=reward/MODEL_TICK; s.rr=rr;
   return true;
}

void AppendSignal(Signal &a[],const Signal &s)
{
   int n=ArraySize(a); ArrayResize(a,n+1); a[n]=s;
}

bool BetterSignal(const Signal &a,const Signal &b)
{
   if(a.rp.priority!=b.rp.priority) return a.rp.priority<b.rp.priority;
   if(MathAbs(a.rr-b.rr)>1e-12) return a.rr>b.rr;
   int c=StringCompare(a.model,b.model);
   if(c!=0) return c<0;
   return StringCompare(a.direction,b.direction)<0;
}
