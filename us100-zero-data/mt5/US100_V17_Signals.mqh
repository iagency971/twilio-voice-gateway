// ---------- raw model creation helpers ----------

bool BuildRaw(int idx,const MqlRates &r[],string model,string dir,string tag,double entry,double stop,double target,Signal &s)
{
   RiskProfile rp;if(!GetProfile(model,rp))return false;
   double risk=MathAbs(entry-stop),reward=MathAbs(target-entry);
   if(!RawRiskOK(risk,reward,rp))return false;
   MakeSignal(idx,r[idx].time,model,dir,tag,entry,stop,target,rp,s);return true;
}

void CandidateFromRaw(Signal &raw,double atr,Signal &cand[])
{
   if(!ApplyATRHybrid(raw,atr))return;
   if(!BranchSelected(raw.model,raw.direction))return;
   if(MinuteOfDay(raw.nyTime)>=15*60+30)return;
   AppendSignal(cand,raw);
}

bool BuildCurrentFinalSignal(Signal &outSignal)
{
   MqlRates r[]; ArraySetAsSeries(r,false);
   int want=MathMax(InpFeatureBars,400);
   int n=CopyRates(_Symbol,PERIOD_M1,1,want,r);
   if(n<250) return false;
   SortRatesAscending(r);
   datetime expected=iTime(_Symbol,PERIOD_M1,1);
   if(r[n-1].time!=expected) {LogEvent("QA_FAIL","","",0,0,0,0,"latest closed M1 mismatch");return false;}

   double vwap[],vwapStd[],ema9[],ema20[],ema21[],devStd[],hurst[],kalLevel[],kalSlope[],theta[],hl[],ouz[],atr[];
   if(!BuildFeatures(r,n,vwap,vwapStd,ema9,ema20,ema21,devStd,hurst,kalLevel,kalSlope,theta,hl,ouz,atr)) return false;

   int curKey=DayKey(NYTime(r[n-1].time)); DailyContext dc;
   if(!BuildDailyContext(r[n-1].time,curKey,dc)||!dc.ready){LogEvent("QA_FAIL","","",0,0,0,0,"daily context unavailable");return false;}
   int dayStart=-1;for(int i=0;i<n;i++){if(DayKey(NYTime(r[i].time))==curKey){dayStart=i;break;}}
   if(dayStart<0)return false;

   int usedEMA=0,usedKal=0,usedOpen=0,usedLunch=0,usedOU=0,usedPD=0,usedPM=0,usedSweep=0,usedTrend=0,usedVR=0,usedVS=0;
   bool odInit=false;double odOpen=0,odHigh=0,odLow=0;int drive=0;
   bool swInit=false;double sessionHigh=0,sessionLow=0;int shIdx=0,slIdx=0;
   int lastAccepted=-1000000; bool found=false;

   for(int i=MathMax(dayStart,2);i<n;i++)
   {
      datetime ny=NYTime(r[i].time);int m=MinuteOfDay(ny);int wd=PyWeekday(ny);Signal cands[];ArrayResize(cands,0);Signal s;
      MqlRates b=r[i],p=r[i-1];

      if(usedEMA<1 && m>=590 && m<870 && ValidD(devStd[i]) && devStd[i]>=2*MODEL_TICK)
      {
         double z=(b.close-ema20[i])/devStd[i];
         if(z<-2.5 && b.close>b.open && b.close>p.low && dc.regime!=-1)
         {double st=MathMin(b.low,p.low)-4*MODEL_TICK,tg=ema20[i];if(tg>b.close&&BuildRaw(i,r,"ema_rev","long","ema_rev_long",b.close,st,tg,s)){usedEMA++;CandidateFromRaw(s,atr[i],cands);}}
         else if(z>2.5 && b.close<b.open && b.close<p.high && dc.regime!=1)
         {double st=MathMax(b.high,p.high)+4*MODEL_TICK,tg=ema20[i];if(tg<b.close&&BuildRaw(i,r,"ema_rev","short","ema_rev_short",b.close,st,tg,s)){usedEMA++;CandidateFromRaw(s,atr[i],cands);}}
      }

      if(usedKal<1 && m>=615 && m<840 && ValidD(hurst[i]) && hurst[i]>=0.50 && ValidD(kalSlope[i]) && ValidD(kalLevel[i]) && MathAbs(kalSlope[i])>=0.3)
      {
         bool cons=true;for(int j=0;j<5;j++){if(i-j<0||!ValidD(kalSlope[i-j])||((kalSlope[i-j]>0)!=(kalSlope[i]>0))){cons=false;break;}}
         if(cons && kalSlope[i]>0.3 && dc.regime!=-1)
         {double st=b.low-4*MODEL_TICK,rk=b.close-st,tg=b.close+rk*2.5;if(rk>0&&BuildRaw(i,r,"kalman_mom","long","kalman_mom_long",b.close,st,tg,s)){usedKal++;CandidateFromRaw(s,atr[i],cands);}}
         else if(cons && kalSlope[i]<-0.3 && dc.regime!=1)
         {double st=b.high+4*MODEL_TICK,rk=st-b.close,tg=b.close-rk*2.5;if(rk>0&&BuildRaw(i,r,"kalman_mom","short","kalman_mom_short",b.close,st,tg,s)){usedKal++;CandidateFromRaw(s,atr[i],cands);}}
      }

      if(m==570 && !odInit){odInit=true;odOpen=b.open;odHigh=b.high;odLow=b.low;drive=0;}
      else if(odInit && m>570 && m<=575)
      {
         odHigh=MathMax(odHigh,b.high);odLow=MathMin(odLow,b.low);
         if(odHigh-odOpen>=5.0)drive=1;else if(odOpen-odLow>=5.0)drive=-1;
      }
      else if(odInit && drive!=0 && usedOpen<2 && m>=576 && m<=615 && ValidD(vwap[i]))
      {
         double slope=kalSlope[i];
         if(drive==1 && dc.regime!=-1 && b.low<=vwap[i]+3*MODEL_TICK && b.close>vwap[i] && b.close>b.open && (!ValidD(slope)||slope>-0.1))
         {double st=MathMin(b.low,odLow)-4*MODEL_TICK,rk=b.close-st,tg=b.close+rk*2.0;if(rk>0&&BuildRaw(i,r,"open_drive","long","open_drive_long",b.close,st,tg,s)){usedOpen++;CandidateFromRaw(s,atr[i],cands);}}
         else if(drive==-1 && dc.regime!=1 && b.high>=vwap[i]-3*MODEL_TICK && b.close<vwap[i] && b.close<b.open && (!ValidD(slope)||slope<0.1))
         {double st=MathMax(b.high,odHigh)+4*MODEL_TICK,rk=st-b.close,tg=b.close-rk*2.0;if(rk>0&&BuildRaw(i,r,"open_drive","short","open_drive_short",b.close,st,tg,s)){usedOpen++;CandidateFromRaw(s,atr[i],cands);}}
      }

      if(usedLunch<3 && m>=690 && m<810 && ValidD(theta[i])&&ValidD(hl[i])&&ValidD(ouz[i])&&ValidD(hurst[i]) && hurst[i]<=0.42 && theta[i]>0 && hl[i]>=2&&hl[i]<=20 && ValidD(vwap[i]))
      {
         if(ouz[i]<-1.8 && b.close>b.open && b.close>p.low && dc.regime!=-1)
         {double st=MathMin(b.low,p.low)-4*MODEL_TICK,tg=vwap[i];if(tg>b.close&&BuildRaw(i,r,"ou_lunch","long","ou_lunch_long",b.close,st,tg,s)){usedLunch++;CandidateFromRaw(s,atr[i],cands);}}
         else if(ouz[i]>1.8 && b.close<b.open && b.close<p.high && dc.regime!=1)
         {double st=MathMax(b.high,p.high)+4*MODEL_TICK,tg=vwap[i];if(tg<b.close&&BuildRaw(i,r,"ou_lunch","short","ou_lunch_short",b.close,st,tg,s)){usedLunch++;CandidateFromRaw(s,atr[i],cands);}}
      }

      if(usedOU<6 && m>=590 && m<900 && !(m>=690&&m<810) && ValidD(theta[i])&&ValidD(hl[i])&&ValidD(ouz[i])&&ValidD(hurst[i]) && hurst[i]<=0.45 && theta[i]>0 && hl[i]>=2&&hl[i]<=25 && ValidD(vwap[i]))
      {
         if(ouz[i]<-2.0 && b.close>b.open && b.close>p.low && dc.regime!=-1)
         {double st=MathMin(b.low,p.low)-4*MODEL_TICK,tg=vwap[i];if(tg>b.close&&BuildRaw(i,r,"ou_rev","long","ou_rev_long",b.close,st,tg,s)){usedOU++;CandidateFromRaw(s,atr[i],cands);}}
         else if(ouz[i]>2.0 && b.close<b.open && b.close<p.high && dc.regime!=1)
         {double st=MathMax(b.high,p.high)+4*MODEL_TICK,tg=vwap[i];if(tg<b.close&&BuildRaw(i,r,"ou_rev","short","ou_rev_short",b.close,st,tg,s)){usedOU++;CandidateFromRaw(s,atr[i],cands);}}
      }

      if(usedPD<1 && m>=590 && m<840 && ValidD(vwap[i]))
      {
         if(dc.regime!=1 && p.high>=dc.pdh-2*MODEL_TICK && b.close<dc.pdh && b.close<b.open && MathAbs(b.close-dc.pdh)<20*MODEL_TICK)
         {double st=MathMax(p.high,b.high)+4*MODEL_TICK,rk=st-b.close,tg=MathMin(vwap[i],b.close-rk*2.0);if(rk>0&&BuildRaw(i,r,"pd_rev","short","pd_pdh_short",b.close,st,tg,s)){usedPD++;CandidateFromRaw(s,atr[i],cands);}}
         else if(dc.regime!=-1 && p.low<=dc.pdl+2*MODEL_TICK && b.close>dc.pdl && b.close>b.open && MathAbs(b.close-dc.pdl)<20*MODEL_TICK)
         {double st=MathMin(p.low,b.low)-4*MODEL_TICK,rk=b.close-st,tg=MathMax(vwap[i],b.close+rk*2.0);if(rk>0&&BuildRaw(i,r,"pd_rev","long","pd_pdl_long",b.close,st,tg,s)){usedPD++;CandidateFromRaw(s,atr[i],cands);}}
      }

      if(usedPM<1 && m>=810 && m<900 && ValidD(kalSlope[i])&&ValidD(kalLevel[i]) && MathAbs(kalSlope[i])>=0.15)
      {
         if(kalSlope[i]>0.15 && b.close>b.open && dc.regime!=-1 && b.low<=kalLevel[i]+5*MODEL_TICK && b.close>kalLevel[i])
         {double st=MathMin(b.low,kalLevel[i])-4*MODEL_TICK,rk=b.close-st,tg=b.close+rk*2.0;if(rk>0&&BuildRaw(i,r,"pm_mom","long","pm_mom_long",b.close,st,tg,s)){usedPM++;CandidateFromRaw(s,atr[i],cands);}}
         else if(kalSlope[i]<-0.15 && b.close<b.open && dc.regime!=1 && b.high>=kalLevel[i]-5*MODEL_TICK && b.close<kalLevel[i])
         {double st=MathMax(b.high,kalLevel[i])+4*MODEL_TICK,rk=st-b.close,tg=b.close-rk*2.0;if(rk>0&&BuildRaw(i,r,"pm_mom","short","pm_mom_short",b.close,st,tg,s)){usedPM++;CandidateFromRaw(s,atr[i],cands);}}
      }

      if(m>=570)
      {
         if(!swInit){swInit=true;sessionHigh=b.high;sessionLow=b.low;shIdx=i;slIdx=i;}
         else {if(b.high>sessionHigh){sessionHigh=b.high;shIdx=i;} if(b.low<sessionLow){sessionLow=b.low;slIdx=i;}}
      }
      if(usedSweep<2 && ((m>=585&&m<660)||(m>=840&&m<900)) && ValidD(vwap[i]))
      {
         bool sweptPDH=(p.high>dc.pdh+MODEL_TICK && p.close<dc.pdh);
         bool sweptSession=(swInit && i-shIdx>3 && p.high>sessionHigh && p.close<sessionHigh);
         if(dc.regime!=1 && (sweptPDH||sweptSession) && (b.open-b.close)>=6*MODEL_TICK && b.close<b.open && b.close<=p.close && b.close<vwap[i])
         {
            double st=MathMax(p.high,b.high)+4*MODEL_TICK,rk=st-b.close,tl=vwap[i];if(dc.pdl<b.close)tl=MathMin(tl,(b.close+dc.pdl)/2.0);double tg=MathMin(tl,b.close-rk*2.5);
            if(rk>0&&BuildRaw(i,r,"sweep","short",sweptPDH?"sweep_pdh_short":"sweep_sh_short",b.close,st,tg,s)){usedSweep++;CandidateFromRaw(s,atr[i],cands);}
         }
         else
         {
            bool sweptPDL=(p.low<dc.pdl-MODEL_TICK && p.close>dc.pdl);
            bool sweptSessL=(swInit && i-slIdx>3 && p.low<sessionLow && p.close>sessionLow);
            if(dc.regime!=-1 && (sweptPDL||sweptSessL) && (b.close-b.open)>=6*MODEL_TICK && b.close>b.open && b.close>=p.close && b.close>vwap[i])
            {
               double st=MathMin(p.low,b.low)-4*MODEL_TICK,rk=b.close-st,tg=MathMax(vwap[i]+(vwap[i]-MathMin(p.low,b.low)),b.close+rk*2.5);
               if(rk>0&&BuildRaw(i,r,"sweep","long","sweep_pdl_long",b.close,st,tg,s)){usedSweep++;CandidateFromRaw(s,atr[i],cands);}
            }
         }
      }

      if(usedTrend<5 && wd!=0 && wd!=4 && ((m>=600&&m<720)||(m>=810&&m<900)) && dc.regime!=0 && (!ValidD(hurst[i])||hurst[i]>=0.50))
      {
         double sep=MathAbs(ema9[i]-ema21[i])/MODEL_TICK;
         if(sep>=5)
         {
            bool aligned=true;for(int j=0;j<10;j++){if(i-j<0||((ema9[i-j]>ema21[i-j])!=(ema9[i]>ema21[i]))){aligned=false;break;}}
            if(aligned)
            {
               if(ema9[i]>ema21[i] && sep>=10 && p.low<=ema9[i]+3*MODEL_TICK && b.close>ema9[i] && b.close>b.open && p.low>ema21[i] && dc.regime==1)
               {
                  double st=MathMin(b.low,p.low)-4*MODEL_TICK,rk=b.close-st,rh=-DBL_MAX;for(int j=MathMax(0,i-20);j<i;j++)rh=MathMax(rh,r[j].high);double tg=MathMax(b.close+rk*2.0,rh);
                  if(rk>0&&BuildRaw(i,r,"trend","long","trend_cont_long",b.close,st,tg,s)){usedTrend++;CandidateFromRaw(s,atr[i],cands);}
               }
               else if(ema9[i]<ema21[i] && p.high>=ema9[i]-3*MODEL_TICK && b.close<ema9[i] && b.close<b.open && p.high<ema21[i])
               {
                  double st=MathMax(b.high,p.high)+4*MODEL_TICK,rk=st-b.close,rl=DBL_MAX;for(int j=MathMax(0,i-20);j<i;j++)rl=MathMin(rl,r[j].low);double tg=MathMin(b.close-rk*2.0,rl);
                  if(rk>0&&BuildRaw(i,r,"trend","short","trend_cont_short",b.close,st,tg,s)){usedTrend++;CandidateFromRaw(s,atr[i],cands);}
               }
            }
         }
      }

      if(usedVR<2 && m>=600 && m<870 && ValidD(vwap[i])&&ValidD(vwapStd[i])&&vwapStd[i]>=2*MODEL_TICK)
      {
         double dist=(b.close-vwap[i])/vwapStd[i];
         if(dist<-2.0 && b.close>b.open && b.close>p.low && dc.regime!=-1)
         {double st=MathMin(b.low,p.low)-4*MODEL_TICK,tg=vwap[i];if(tg>b.close&&BuildRaw(i,r,"vwap_rev","long","vwap_rev_long",b.close,st,tg,s)){usedVR++;CandidateFromRaw(s,atr[i],cands);}}
         else if(dist>2.0 && b.close<b.open && b.close<p.high && dc.regime!=1)
         {double st=MathMax(b.high,p.high)+4*MODEL_TICK,tg=vwap[i];if(tg<b.close&&BuildRaw(i,r,"vwap_rev","short","vwap_rev_short",b.close,st,tg,s)){usedVR++;CandidateFromRaw(s,atr[i],cands);}}
      }

      if(usedVS<3 && m>=600 && m<840 && ValidD(vwap[i])&&ValidD(ouz[i])&&ValidD(hurst[i])&&hurst[i]<=0.48)
      {
         if(ouz[i]>-2.5 && ouz[i]<-1.5 && b.close>b.open && b.close>p.low && dc.regime!=-1)
         {double st=MathMin(b.low,p.low)-4*MODEL_TICK,tg=b.close+(vwap[i]-b.close)*0.5;if(tg>b.close&&BuildRaw(i,r,"vwap_scalp","long","vwap_scalp_long",b.close,st,tg,s)){usedVS++;CandidateFromRaw(s,atr[i],cands);}}
         else if(ouz[i]>1.5 && ouz[i]<2.5 && b.close<b.open && b.close<p.high && dc.regime!=1)
         {double st=MathMax(b.high,p.high)+4*MODEL_TICK,tg=b.close-(b.close-vwap[i])*0.5;if(tg<b.close&&BuildRaw(i,r,"vwap_scalp","short","vwap_scalp_short",b.close,st,tg,s)){usedVS++;CandidateFromRaw(s,atr[i],cands);}}
      }

      int cn=ArraySize(cands);
      if(cn>0)
      {
         int best=0;for(int k=1;k<cn;k++)if(BetterSignal(cands[k],cands[best]))best=k;
         if(i-lastAccepted>=3)
         {
            lastAccepted=i;
            if(QualityPass(cands[best],hurst,hl,ouz) && i==n-1){outSignal=cands[best];found=true;}
         }
      }
   }
   return found;
}
