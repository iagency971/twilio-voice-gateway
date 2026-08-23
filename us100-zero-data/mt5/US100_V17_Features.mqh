// ---------- rolling math / features ----------

double RollingVar(const double &a[],int i,int window,int minp,bool sample)
{
   int from=MathMax(0,i-window+1); int n=0; double sum=0.0,sum2=0.0;
   for(int j=from;j<=i;j++)
   {
      if(!ValidD(a[j])) continue;
      n++; sum+=a[j]; sum2+=a[j]*a[j];
   }
   if(n<minp || (sample && n<2)) return EMPTY_VALUE;
   double num=sum2-sum*sum/n;
   if(num<0 && num>-1e-10) num=0;
   if(num<0) return EMPTY_VALUE;
   return num/(sample?(n-1):n);
}

double RollingStd(const double &a[],int i,int window,int minp,bool sample)
{
   double v=RollingVar(a,i,window,minp,sample);
   return ValidD(v)?MathSqrt(v):EMPTY_VALUE;
}

bool BuildFeatures(const MqlRates &r[],int n,
                   double &vwap[],double &vwapStd[],double &ema9[],double &ema20[],double &ema21[],
                   double &devStd20[],double &hurst[],double &kalLevel[],double &kalSlope[],
                   double &ouTheta[],double &ouHL[],double &ouZ[],double &atr5[])
{
   if(n<200) return false;
   ArrayResize(vwap,n);ArrayResize(vwapStd,n);ArrayResize(ema9,n);ArrayResize(ema20,n);ArrayResize(ema21,n);
   ArrayResize(devStd20,n);ArrayResize(hurst,n);ArrayResize(kalLevel,n);ArrayResize(kalSlope,n);
   ArrayResize(ouTheta,n);ArrayResize(ouHL,n);ArrayResize(ouZ,n);ArrayResize(atr5,n);
   double dev[],ret1[],ret16[],x[],dx[],xlag[],resid[],tr[];
   ArrayResize(dev,n);ArrayResize(ret1,n);ArrayResize(ret16,n);ArrayResize(x,n);ArrayResize(dx,n);
   ArrayResize(xlag,n);ArrayResize(resid,n);ArrayResize(tr,n);
   for(int i=0;i<n;i++)
   {
      devStd20[i]=hurst[i]=ouTheta[i]=ouHL[i]=ouZ[i]=atr5[i]=EMPTY_VALUE;
      ret1[i]=ret16[i]=dx[i]=xlag[i]=resid[i]=EMPTY_VALUE;
   }

   double k9=2.0/10.0,k20=2.0/21.0,k21=2.0/22.0;
   ema9[0]=ema20[0]=ema21[0]=r[0].close;

   double x0=r[0].close,x1=0.0,p00=100.0,p01=0.0,p11=1.0;
   kalLevel[0]=x0; kalSlope[0]=x1;

   int prevSessKey=-1; bool prevRth=false; bool sessInit=false;
   double cumVol=0.0,cumTPVol=0.0,cumSq=0.0;

   for(int i=0;i<n;i++)
   {
      if(i>0)
      {
         ema9[i]=r[i].close*k9+ema9[i-1]*(1.0-k9);
         ema20[i]=r[i].close*k20+ema20[i-1]*(1.0-k20);
         ema21[i]=r[i].close*k21+ema21[i-1]*(1.0-k21);

         double xp0=x0+x1, xp1=x1;
         double pp00=p00+2.0*p01+p11+1.0;
         double pp01=p01+p11;
         double pp11=p11+0.01;
         double y=r[i].close-xp0;
         double sinv=1.0/(pp00+2.0);
         double k0=pp00*sinv,k1=pp01*sinv;
         x0=xp0+k0*y; x1=xp1+k1*y;
         p00=(1.0-k0)*pp00; p01=(1.0-k0)*pp01; p11=pp11-k1*pp01;
         kalLevel[i]=x0; kalSlope[i]=x1;
      }

      datetime ny=NYTime(r[i].time); int dkey=DayKey(ny); bool rth=(MinuteOfDay(ny)>=570);
      if(!sessInit || dkey!=prevSessKey || rth!=prevRth)
      {
         cumVol=0;cumTPVol=0;cumSq=0;prevSessKey=dkey;prevRth=rth;sessInit=true;
      }
      double vol=(double)r[i].tick_volume; if(vol<=0) vol=1.0;
      double tp=(r[i].high+r[i].low+r[i].close)/3.0;
      cumVol+=vol; cumTPVol+=tp*vol; vwap[i]=cumTPVol/cumVol;
      double d=tp-vwap[i]; cumSq+=d*d*vol; vwapStd[i]=MathSqrt(cumSq/cumVol);

      dev[i]=r[i].close-ema20[i];
      devStd20[i]=RollingStd(dev,i,20,10,true);

      if(i>=1) {ret1[i]=r[i].close-r[i-1].close; x[i]=r[i].close-vwap[i]; dx[i]=x[i]-(r[i-1].close-vwap[i-1]); xlag[i]=r[i-1].close-vwap[i-1];}
      else x[i]=r[i].close-vwap[i];
      if(i>=16) ret16[i]=r[i].close-r[i-16].close;

      double v1=RollingVar(ret1,i,120,40,true),v16=RollingVar(ret16,i,120,40,true);
      if(ValidD(v1)&&ValidD(v16)&&v1>0&&v16>0) hurst[i]=MathLog(MathMax(v16/v1,1e-10))/(2.0*MathLog(16.0));

      if(i>=1)
      {
         int from=MathMax(1,i-59),cnt=0; double md=0,mx=0,mp=0,mx2=0;
         for(int j=from;j<=i;j++)
         {
            if(!ValidD(dx[j])||!ValidD(xlag[j])) continue;
            cnt++; md+=dx[j]; mx+=xlag[j]; mp+=dx[j]*xlag[j]; mx2+=xlag[j]*xlag[j];
         }
         if(cnt>=30)
         {
            md/=cnt; mx/=cnt; mp/=cnt; mx2/=cnt;
            double vx=mx2-mx*mx;
            if(vx>1e-14)
            {
               double beta=(mp-md*mx)/vx;
               double theta=-beta;
               ouTheta[i]=theta;
               if(theta>0) ouHL[i]=MathLog(2.0)/theta;
               resid[i]=dx[i]-beta*xlag[i];
               double rs=RollingStd(resid,i,60,30,true);
               if(theta>0 && ValidD(rs))
               {
                  double sigma=rs/MathSqrt(MathMax(2.0*theta,1e-10));
                  if(sigma>0 && MathIsValidNumber(sigma)) ouZ[i]=x[i]/sigma;
               }
            }
         }
      }

      double pc=(i>0?r[i-1].close:r[i].close);
      tr[i]=MathMax(r[i].high-r[i].low,MathMax(MathAbs(r[i].high-pc),MathAbs(r[i].low-pc)));
      if(i>=4)
      {
         double s=0; for(int j=i-4;j<=i;j++) s+=tr[j]; atr5[i]=s/5.0;
      }
   }
   return true;
}

// ---------- RTH daily context ----------

bool BuildDailyContext(datetime serverNow,int currentNYKey,DailyContext &ctx)
{
   ctx.ready=false;ctx.pdh=ctx.pdl=ctx.prevClose=0;ctx.regime=0;ctx.previousDayKey=0;
   datetime from=serverNow-(long)InpDailyLookbackDays*86400;
   MqlRates rr[]; ArraySetAsSeries(rr,false);
   int n=CopyRates(_Symbol,PERIOD_M5,from,serverNow,rr);
   if(n<=0) return false;
   SortRatesAscending(rr);
   DayAgg d[]; int dn=0;
   for(int i=0;i<n;i++)
   {
      datetime ny=NYTime(rr[i].time); int m=MinuteOfDay(ny);
      if(m<570 || m>=960) continue;
      int key=DayKey(ny);
      if(dn==0 || d[dn-1].key!=key)
      {
         ArrayResize(d,dn+1); d[dn].key=key;d[dn].high=rr[i].high;d[dn].low=rr[i].low;d[dn].close=rr[i].close;d[dn].count=1;dn++;
      }
      else
      {
         int k=dn-1; if(rr[i].high>d[k].high)d[k].high=rr[i].high; if(rr[i].low<d[k].low)d[k].low=rr[i].low;
         d[k].close=rr[i].close; d[k].count++;
      }
   }
   int p=-1; for(int i=dn-1;i>=0;i--) if(d[i].key<currentNYKey){p=i;break;}
   if(p<50) return false;
   double e20=d[0].close,e50=d[0].close,k20=2.0/21.0,k50=2.0/51.0;
   for(int i=1;i<=p;i++) {e20=d[i].close*k20+e20*(1-k20);e50=d[i].close*k50+e50*(1-k50);}
   ctx.pdh=d[p].high;ctx.pdl=d[p].low;ctx.prevClose=d[p].close;ctx.previousDayKey=d[p].key;
   bool a20=ctx.prevClose>e20,a50=ctx.prevClose>e50;
   ctx.regime=(a20&&a50?1:((!a20&&!a50)?-1:0)); ctx.ready=true;
   return true;
}

// ---------- signal quality ----------

bool QualityPass(const Signal &s,const double &hurst[],const double &ouHL[],const double &ouZ[])
{
   if(s.model!="ou_rev") return true;
   int score=0;
   if(s.direction=="long") score+=1;
   int wd=PyWeekday(s.nyTime);
   if(wd==3) score+=1; else if(wd==4) score+=2; else if(wd==2) score-=1;
   int hr=HourOf(s.nyTime); if(hr==10||hr==14)score+=1;
   int i=s.idx;
   if(ValidD(ouHL[i])) {if(ouHL[i]<=5)score+=3; else if(ouHL[i]<=10)score+=1; else score-=3;}
   if(ValidD(ouZ[i]))
   {
      double z=MathAbs(ouZ[i]); if(z>=2.0&&z<=2.5)score+=2; else if(z>2.5&&z<=3.0)score+=1; else if(z>3.0)score-=1;
   }
   if(ValidD(hurst[i])) {if(hurst[i]<0.35)score+=3; else if(hurst[i]<0.40)score+=2; else if(hurst[i]<0.45)score+=1; else if(hurst[i]>=0.50)score-=1;}
   if(s.rr>=2.0-1e-12&&s.rr<=2.5+1e-12)score+=1;
   return score>=3;
}
