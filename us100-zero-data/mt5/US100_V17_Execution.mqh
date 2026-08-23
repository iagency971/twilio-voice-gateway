// ---------- engine / account-state helpers ----------

bool OwnPosition(ulong &ticket)
{
   ticket=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong t=PositionGetTicket(i);if(t==0||!PositionSelectByTicket(t))continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol)continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic)continue;
      ticket=t;return true;
   }
   return false;
}

double DailyClosedPnL(datetime serverNow)
{
   datetime start=NYDayStartServer(serverNow);if(!HistorySelect(start,serverNow))return 0.0;
   double p=0.0;int n=HistoryDealsTotal();
   for(int i=0;i<n;i++)
   {
      ulong d=HistoryDealGetTicket(i);if(d==0)continue;
      if(HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol)continue;
      if((ulong)HistoryDealGetInteger(d,DEAL_MAGIC)!=InpMagic)continue;
      p+=HistoryDealGetDouble(d,DEAL_PROFIT)+HistoryDealGetDouble(d,DEAL_COMMISSION)+HistoryDealGetDouble(d,DEAL_SWAP)+HistoryDealGetDouble(d,DEAL_FEE);
   }
   return p;
}

string GV(string suffix){return "V17_"+(string)InpMagic+"_"+_Symbol+"_"+suffix;}

void SavePositionState()
{
   if(!g_ps.active)return;
   GlobalVariableSet(GV("active"),1);GlobalVariableSet(GV("dir"),(double)g_ps.direction);GlobalVariableSet(GV("entry"),g_ps.entry);
   GlobalVariableSet(GV("base"),g_ps.baseStop);GlobalVariableSet(GV("target"),g_ps.target);GlobalVariableSet(GV("risk"),g_ps.risk);GlobalVariableSet(GV("riskusd"),g_ps.riskDollars);
   GlobalVariableSet(GV("mfe"),g_ps.mfe);GlobalVariableSet(GV("trailstop"),g_ps.trailStop);GlobalVariableSet(GV("be"),g_ps.be?1:0);
   GlobalVariableSet(GV("trailing"),g_ps.trailing?1:0);GlobalVariableSet(GV("betrig"),g_ps.beTrigger);GlobalVariableSet(GV("partial"),g_ps.partialRR);
   GlobalVariableSet(GV("trailpct"),g_ps.trailPct);GlobalVariableSet(GV("timestop"),(double)g_ps.timeStopMin);GlobalVariableSet(GV("entrytime"),(double)g_ps.entryTime);
   GlobalVariableSet(GV("modelid"),(double)ModelId(g_ps.model));
}

void ClearPositionState()
{
   string ss[]={"active","dir","entry","base","target","risk","riskusd","mfe","trailstop","be","trailing","betrig","partial","trailpct","timestop","entrytime","modelid"};
   for(int i=0;i<ArraySize(ss);i++)GlobalVariableDel(GV(ss[i]));
   ZeroMemory(g_ps);g_ps.active=false;
}

bool LoadPositionState()
{
   if(!GlobalVariableCheck(GV("active"))||GlobalVariableGet(GV("active"))<0.5)return false;
   g_ps.active=true;g_ps.direction=(long)GlobalVariableGet(GV("dir"));g_ps.entry=GlobalVariableGet(GV("entry"));g_ps.baseStop=GlobalVariableGet(GV("base"));
   g_ps.target=GlobalVariableGet(GV("target"));g_ps.risk=GlobalVariableGet(GV("risk"));g_ps.riskDollars=GlobalVariableCheck(GV("riskusd"))?GlobalVariableGet(GV("riskusd")):InpRiskDollars;g_ps.mfe=GlobalVariableGet(GV("mfe"));g_ps.trailStop=GlobalVariableGet(GV("trailstop"));
   g_ps.be=GlobalVariableGet(GV("be"))>0.5;g_ps.trailing=GlobalVariableGet(GV("trailing"))>0.5;g_ps.beTrigger=GlobalVariableGet(GV("betrig"));
   g_ps.partialRR=GlobalVariableGet(GV("partial"));g_ps.trailPct=GlobalVariableGet(GV("trailpct"));g_ps.timeStopMin=(int)GlobalVariableGet(GV("timestop"));g_ps.entryTime=(datetime)GlobalVariableGet(GV("entrytime"));
   g_ps.model=GlobalVariableCheck(GV("modelid"))?ModelName((int)GlobalVariableGet(GV("modelid"))):"";
   return g_ps.risk>0;
}

void SaveConsec(){GlobalVariableSet(GV("consec"),(double)g_consecLosses);}
void LoadConsec(){g_consecLosses=GlobalVariableCheck(GV("consec"))?(int)GlobalVariableGet(GV("consec")):0;}

bool CalculateVolume(ENUM_ORDER_TYPE type,double entry,double stop,double &volume)
{
   volume=0;double one=0;if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one))return false;
   double loss=MathAbs(one);if(loss<=0)return false;volume=NormalizeVolumeDown(InpRiskDollars/loss);return volume>0;
}

bool InitialStopValid(long dir,double entry,double stop)
{
   if(dir>0 && stop>=entry)return false;if(dir<0 && stop<=entry)return false;
   int lv=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);double md=lv*_Point;
   return md<=0 || MathAbs(entry-stop)>=md;
}

bool EngineEntryValidation(const Signal &s,double entryRef,string &why)
{
   double risk=MathAbs(entryRef-s.stop);if(risk<=0){why="nonpositive fill risk";return false;}
   double ticks=risk/MODEL_TICK;double floorTicks=MathMax(s.rp.minTicks,(double)GLOBAL_MIN_RISK_TICKS);double ceilTicks=MathMin(s.rp.maxTicks,(double)GLOBAL_MAX_RISK_TICKS);
   if(ticks<floorTicks-1e-9||ticks>ceilTicks+1e-9){why="actual-fill risk outside frozen tick bounds";return false;}
   double reward=MathAbs(s.target-entryRef);if(reward/risk<s.rp.minRR-1e-12){why="actual-fill RR below model minimum";return false;}
   return true;
}

double ActualStopRiskDollars(long dir,double volume,double entry,double stop)
{
   ENUM_ORDER_TYPE type=(dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);
   double p=0.0;
   if(volume<=0 || !OrderCalcProfit(type,_Symbol,volume,entry,stop,p)) return -1.0;
   return MathAbs(p);
}

bool CloseOwn(string reason)
{
   ulong t=0;if(!OwnPosition(t))return true;
   bool ok=g_trade.PositionClose(t);LogEvent(ok?"POSITION_CLOSE":"POSITION_CLOSE_FAIL",g_ps.model,g_ps.direction>0?"long":"short",0,g_ps.entry,g_ps.baseStop,g_ps.target,reason+(ok?"":(" | "+g_trade.ResultRetcodeDescription())));
   return ok;
}

void SyncBrokerProtection(ulong ticket,double virtualStop,double target)
{
   if(!PositionSelectByTicket(ticket))return;MqlTick tk;if(!SymbolInfoTick(_Symbol,tk))return;
   double px=(g_ps.direction>0?tk.bid:tk.ask);int lv=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);double md=lv*_Point;
   if(g_ps.direction>0 && virtualStop>=px-md)return;if(g_ps.direction<0 && virtualStop<=px+md)return;
   double bs=BrokerStopOutward(g_ps.direction,virtualStop);double bt=(target>0?BrokerPriceNearest(target):0.0);
   double oldsl=PositionGetDouble(POSITION_SL),oldtp=PositionGetDouble(POSITION_TP);
   if(MathAbs(oldsl-bs)<BrokerTickSize()*0.25 && MathAbs(oldtp-bt)<BrokerTickSize()*0.25)return;
   g_trade.PositionModify(ticket,bs,bt);
}

void ManagePosition()
{
   ulong ticket=0;if(!OwnPosition(ticket)){if(g_ps.active)ClearPositionState();return;}
   if(!g_ps.active && !LoadPositionState()){LogEvent("STATE_MISSING","","",0,0,0,0,"position exists but V17 state unavailable");return;}
   MqlTick tk;if(!SymbolInfoTick(_Symbol,tk))return;double px=(g_ps.direction>0?tk.bid:tk.ask);
   if(px<=0)return;

   if(!g_ps.trailing && ((g_ps.direction>0&&px>=g_ps.target)||(g_ps.direction<0&&px<=g_ps.target))) {CloseOwn("virtual target");return;}

   double fav=(g_ps.direction>0?px-g_ps.entry:g_ps.entry-px);if(fav>g_ps.mfe)g_ps.mfe=fav;
   if(!g_ps.trailing && g_ps.mfe>=g_ps.risk*g_ps.partialRR)
   {
      g_ps.trailing=true;
      if(PositionSelectByTicket(ticket)) g_trade.PositionModify(ticket,PositionGetDouble(POSITION_SL),0.0);
   }
   if(!g_ps.be && g_ps.mfe>=g_ps.risk*g_ps.beTrigger)g_ps.be=true;

   double vs=g_ps.baseStop;
   if(g_ps.be) vs=(g_ps.direction>0?MathMax(vs,g_ps.entry):MathMin(vs,g_ps.entry));
   if(g_ps.trailing)
   {
      double ts=(g_ps.direction>0?g_ps.entry+g_ps.mfe-g_ps.trailPct*g_ps.risk:g_ps.entry-g_ps.mfe+g_ps.trailPct*g_ps.risk);
      ts=LogicalRound(ts);g_ps.trailStop=ts;vs=(g_ps.direction>0?MathMax(vs,ts):MathMin(vs,ts));
   }
   if((g_ps.direction>0&&px<=vs)||(g_ps.direction<0&&px>=vs)){CloseOwn(g_ps.trailing?"virtual trail":(g_ps.be?"virtual breakeven":"virtual stop"));return;}

   datetime now=TimeTradeServer();
   if(!g_ps.be && now>=g_ps.entryTime+g_ps.timeStopMin*60){CloseOwn("time stop");return;}
   if(MinuteOfDay(NYTime(now))>=1019){CloseOwn("16:59 NY session close");return;}
   SyncBrokerProtection(ticket,vs,g_ps.trailing?0.0:g_ps.target);SavePositionState();
}

void ExecuteSignal(const Signal &s)
{
   LogEvent("FINAL_SIGNAL",s.model,s.direction,0,s.entry,s.stop,s.target,s.tag);
   if(!InpAllowTrading){LogEvent("SHADOW_ONLY",s.model,s.direction,0,s.entry,s.stop,s.target,"trading disabled");return;}
   ulong t=0;if(OwnPosition(t)){LogEvent("ENGINE_SKIP",s.model,s.direction,0,s.entry,s.stop,s.target,"position overlap");return;}
   double dr=DailyClosedPnL(TimeTradeServer())/InpRiskDollars;if(dr>=InpDailyWinCapR-1e-12){LogEvent("ENGINE_SKIP",s.model,s.direction,0,s.entry,s.stop,s.target,"daily win cap reached");return;}
   if(g_consecLosses>=10){g_consecLosses=0;SaveConsec();LogEvent("ENGINE_SKIP",s.model,s.direction,0,s.entry,s.stop,s.target,"10-loss cooldown skip/reset");return;}

   MqlTick tk;if(!SymbolInfoTick(_Symbol,tk))return;long dir=(s.direction=="long"?1:-1);double ref=(dir>0?tk.ask:tk.bid);string why;
   if(!EngineEntryValidation(s,ref,why)){LogEvent("ENGINE_SKIP",s.model,s.direction,0,ref,s.stop,s.target,why);return;}
   if(!InitialStopValid(dir,ref,s.stop)){LogEvent("ENGINE_SKIP",s.model,s.direction,0,ref,s.stop,s.target,"broker initial stop invalid");return;}
   ENUM_ORDER_TYPE ot=(dir>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL);double vol=0;if(!CalculateVolume(ot,ref,s.stop,vol)){LogEvent("ENGINE_SKIP",s.model,s.direction,0,ref,s.stop,s.target,"volume calc failed/below min");return;}
   double bsl=BrokerStopOutward(dir,s.stop),btp=BrokerPriceNearest(s.target);string comment="V17|"+s.model+"|"+(dir>0?"L":"S");bool sent=(dir>0?g_trade.Buy(vol,_Symbol,0,bsl,btp,comment):g_trade.Sell(vol,_Symbol,0,bsl,btp,comment));
   if(!sent){LogEvent("ORDER_REJECTED",s.model,s.direction,vol,ref,s.stop,s.target,g_trade.ResultRetcodeDescription());return;}
   ulong ticket=0;if(!OwnPosition(ticket)||!PositionSelectByTicket(ticket)){LogEvent("ORDER_SENT_NO_POSITION",s.model,s.direction,vol,ref,s.stop,s.target,g_trade.ResultRetcodeDescription());return;}
   double actual=PositionGetDouble(POSITION_PRICE_OPEN);if(!EngineEntryValidation(s,actual,why)){LogEvent("FILL_PARITY_ABORT",s.model,s.direction,PositionGetDouble(POSITION_VOLUME),actual,s.stop,s.target,why);g_trade.PositionClose(ticket);return;}
   double actualRiskDollars=ActualStopRiskDollars(dir,PositionGetDouble(POSITION_VOLUME),actual,s.stop);
   if(actualRiskDollars>0 && actualRiskDollars>InpRiskDollars*(1.0+InpMaxRiskOvershootPct/100.0)+1e-8)
   {
      LogEvent("FILL_RISK_ABORT",s.model,s.direction,PositionGetDouble(POSITION_VOLUME),actual,s.stop,s.target,"actual SL risk="+DoubleToString(actualRiskDollars,2));
      g_trade.PositionClose(ticket);return;
   }
   ZeroMemory(g_ps);g_ps.active=true;g_ps.direction=dir;g_ps.entry=actual;g_ps.baseStop=s.stop;g_ps.target=s.target;g_ps.risk=MathAbs(actual-s.stop);g_ps.riskDollars=(actualRiskDollars>0?actualRiskDollars:InpRiskDollars);g_ps.mfe=0;g_ps.trailStop=s.stop;g_ps.be=false;g_ps.trailing=false;g_ps.beTrigger=s.rp.beTrigger;g_ps.partialRR=s.rp.partialRR;g_ps.trailPct=s.rp.trailPct;g_ps.timeStopMin=s.rp.timeStopMin;g_ps.entryTime=(datetime)PositionGetInteger(POSITION_TIME);g_ps.model=s.model;SavePositionState();
   LogEvent("ORDER_FILLED",s.model,s.direction,PositionGetDouble(POSITION_VOLUME),actual,s.stop,s.target,"V17 live fill accepted");
}

int OnInit()
{
   if(InpRiskDollars<=0.0 || InpFeatureBars<400 || InpDailyLookbackDays<120 || InpMaxRiskOvershootPct<0.0)
   {
      Print("V17 F1 invalid inputs");
      return INIT_PARAMETERS_INCORRECT;
   }
   g_trade.SetExpertMagicNumber(InpMagic);g_trade.SetTypeFillingBySymbol(_Symbol);g_trade.SetAsyncMode(false);LoadConsec();
   ulong t=0;if(OwnPosition(t))LoadPositionState();else ClearPositionState();
   g_lastClosedBar=iTime(_Symbol,PERIOD_M1,1);
   LogEvent("EA_INIT","","",0,0,0,0,"V17 14-branch causal forward candidate; attach before NY RTH where possible");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason){LogEvent("EA_DEINIT","","",0,0,0,0,"reason="+(string)reason);}

void OnTick()
{
   ManagePosition();
   datetime closed=iTime(_Symbol,PERIOD_M1,1);if(closed<=0||closed==g_lastClosedBar)return;g_lastClosedBar=closed;
   Signal s;if(BuildCurrentFinalSignal(s))ExecuteSignal(s);
}

void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD||trans.deal==0)return;
   if(!HistoryDealSelect(trans.deal))return;
   if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol)return;
   if((ulong)HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic)return;
   long e=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);if(e!=DEAL_ENTRY_OUT&&e!=DEAL_ENTRY_OUT_BY)return;
   double net=HistoryDealGetDouble(trans.deal,DEAL_PROFIT)+HistoryDealGetDouble(trans.deal,DEAL_COMMISSION)+HistoryDealGetDouble(trans.deal,DEAL_SWAP)+HistoryDealGetDouble(trans.deal,DEAL_FEE);
   double lossRef=(g_ps.active&&g_ps.riskDollars>0?g_ps.riskDollars:InpRiskDollars);
   if(net<=-0.5*lossRef)g_consecLosses++;else g_consecLosses=0;SaveConsec();
   LogEvent("DEAL_CLOSED",g_ps.model,g_ps.direction>0?"long":"short",0,g_ps.entry,g_ps.baseStop,g_ps.target,"net="+DoubleToString(net,2)+" consec="+(string)g_consecLosses);
   ulong t=0;if(!OwnPosition(t))ClearPositionState();
}
