"""
AI Insights Service - Main Orchestrator

Orchestrates all AI-powered cost analysis components including anomaly detection,
trend analysis, forecasting, and recommendation generation.
"""

import logging
import math
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum

try:
    from ..models.multi_cloud_models import UnifiedCostRecord
    from ..models.config_models import ClientConfig
    from ..utils.logging import create_logger as get_logger
    from .bedrock_service import BedrockService
    from .anomaly_detection_engine import AnomalyDetectionEngine, Anomaly
    from .trend_analysis_service import TrendAnalyzer, TrendAnalysis
    from .forecasting_engine import ForecastingEngine, ForecastResult
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.multi_cloud_models import UnifiedCostRecord
    from models.config_models import ClientConfig
    from utils.logging import create_logger
    from bedrock_service import BedrockService
    from anomaly_detection_engine import AnomalyDetectionEngine, Anomaly
    from trend_analysis_service import TrendAnalyzer, TrendAnalysis
    from forecasting_engine import ForecastingEngine, ForecastResult
    
    def get_logger(name):
        return create_logger(name)

logger = get_logger(__name__)


class InsightCategory(Enum):
    """Categories for insight classification"""
    ANOMALY = "anomaly"
    TREND = "trend"
    FORECAST = "forecast"
    RECOMMENDATION = "recommendation"
    RISK = "risk"
    OPPORTUNITY = "opportunity"


class InsightPriority(Enum):
    """Priority levels for insights"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AggregatedInsight:
    """Aggregated insight with enhanced metadata"""
    id: str
    category: InsightCategory
    priority: InsightPriority
    title: str
    description: str
    confidence_score: float
    business_impact_score: float
    actionability_score: float
    severity_score: float
    estimated_savings: float
    affected_services: List[str]
    related_insights: List[str]
    metadata: Dict[str, Any]
    timestamp: datetime


class InsightAggregator:
    """
    Advanced insight aggregation engine that combines insights from multiple sources
    and creates unified, actionable insights with proper deduplication and correlation.
    """
    
    def __init__(self):
        self.deduplication_threshold = 0.8
        self.correlation_threshold = 0.7
        
    def aggregate_insights(
        self,
        anomalies: List[Anomaly],
        trends: TrendAnalysis,
        forecasts: ForecastResult,
        recommendations: List['Recommendation'],
        cost_data: List[UnifiedCostRecord]
    ) -> List[AggregatedInsight]:
        """
        Aggregate insights from all analysis components
        
        Args:
            anomalies: Detected anomalies
            trends: Trend analysis results
            forecasts: Forecast results
            recommendations: Generated recommendations
            cost_data: Historical cost data
            
        Returns:
            List of aggregated insights
        """
        aggregated_insights = []
        
        # Convert anomalies to insights
        anomaly_insights = self._convert_anomalies_to_insights(anomalies, cost_data)
        aggregated_insights.extend(anomaly_insights)
        
        # Convert trends to insights
        trend_insights = self._convert_trends_to_insights(trends, cost_data)
        aggregated_insights.extend(trend_insights)
        
        # Convert forecasts to insights
        forecast_insights = self._convert_forecasts_to_insights(forecasts, cost_data)
        aggregated_insights.extend(forecast_insights)
        
        # Convert recommendations to insights
        recommendation_insights = self._convert_recommendations_to_insights(recommendations)
        aggregated_insights.extend(recommendation_insights)
        
        # Deduplicate and correlate insights
        deduplicated_insights = self._deduplicate_insights(aggregated_insights)
        correlated_insights = self._correlate_insights(deduplicated_insights)
        
        return correlated_insights
    
    def _convert_anomalies_to_insights(
        self, 
        anomalies: List[Anomaly], 
        cost_data: List[UnifiedCostRecord]
    ) -> List[AggregatedInsight]:
        """Convert anomalie"
        insights = []
        
        for i, anomaly in enies):
s

            
            # Calculate actionability based on recommended actions
     0.3
            
           re
            severity_map = {'critical': 4}
        )
            
            insight = AggregatedInsight(
           }",
                category=InsANOMALY,
        lue),
                title=f"Anomaly Detected: {an
                description=anomaly.descrip
                confidence_score=an
                business_impact_sc,
                actionability_score=actionability,
                severity_score=severity_score,
                estimated_savings=abs(anle
                affected_services=anomaly.affecte
              ,
                metadata={
                    'anomaly_typealue,
                    'detection_method': anomaly.detection_method,
                    'cost_impact': anomaly.cost_impact,
                    'recommended_actions':
                },
              amp
            )
            insights.append(insight)
        
        return insights
    
    def _convert_trends_to_insights(
        self, 
        trends: TrendAnalysis, 
        cost_data: List[UnifiedC
    ) -> List[AggregatedInsight]:
        """Convert trend analysis to aggregated 
        insights = []
        
        # Overight
        if trends.overall_trend.signif:
            priority = InsightPr
            
            insight = AggregatedInsight(
                id="trend_overall",
                category=InsightCategory.TREND,
              
                title=f"Overall Cost T",
                description=f"C",
                confidence_score=trends.trend_confidence,
                business_impact_score=min(abs(trends.ove
                actionability_score=0.7,
                severity_score=min(abs(trends.o30, 1.0),
             
         
        
                metadata={
                    'growth_
                    'volatility':y,
                    'trend_strength': trends.overall_trend.trend_strength
                },
                timestamp=datetime.utcnow()
            )
            insights.append(insight)
        
        # Service-specific trend insights (t
        service_trends_sorted = sorted(
            tr),
            key=lambda x: abs(x[1]
            reverse=True
        )
        
        for i]):
         um']:
        UM
                
                insight = Aggregnsight(
                    id=f"trend_ce}",
                    category=InsightCat
                    priority=pity,
                    title=f"
                    description=f"{,
         strength,
        .0),
                  =0.8,
                 1.0),
                    estimated_savings=0,
                    affected_services=[service],
                    related_insighs=[],
                    metadata={
                        'service': service,
    owth_rate,
                        'volatiliity
              
                    timestamp=datetime.utcnow()
                )
                insights.appent)
        
        return insights
    
    def _coghts(
        self, 
        sult, 
        cost_rd]
    ) -> List[AggregatedInsight]:
        """Convert forecast results to ag
        insights = []
        
        if forecasts.accuracy_assessment.value in ['high', 'medium']:
            ta else 0
            fore 0)
            
           :
                change_perce0
        
            
                    priority = InsightPrior
                    
                    insight = AggregatedInsight(
                        id="forecast_overall",
             
                        priority=priority,
            ",
                        description=f"Forecasted 
                        confidence_score=forecasts.total_forec
                        business_impact_score=min(abs(change_percentage)  1.0),
                        actionability_score=
             
                        estimated_savings=0,
            
                        related_insights=[],
                        metadata={
                            'forecast_amount': forecast_amount,
                            'current
             
                            'forecast_period': forecasts.food
            ,
                        timestamp=datetime.utnow()
                    )
                    insights.append(insight)
        
        retur
    
    def _conts(
        self, 
        recommendations: List['Recommendation']
    ) -> List[AggregatedInsight]:
        """Convert recommendations to aggreg"
        insig]
        
        for ns):
            # Map recommendation priority to insight priory
            priority_map = 
                'critical': InsightPriority.CRITICAL,
                'high': InsightPriority.HIGH,
                'medium': InsightPriority.MEDIUM,
                '
            }
            
            # Calculate actionability based on impl
            effort_to_actionability = {'low': 0.9, 'medium': 0.7, 'high': 0.4}
            actionability = effort_to_actionability.get(re
            
            ht(
                id=f"recommendation_{i}",
                category=InsightCategoryON,
            UM),
                title=rec.titl
                description=rec.description,
                confidence_score=rec.confidence_score,
    $1000
                actionability_score=actionability,
              s
                estimated_savings=rec.estim
                affected_services,
                related_insights=[],
                metadata={
                    'category': rec.category,
                    'implement,
                    'implementation_steps': rec.implementation_steps
                },
        tcnow()
            )
            insights.append(insight)
        
        return insights
    
    def _deduplicate_insights(self, insights: List[AggregatedInsight]) ->
        "
        if not insights:
            return insights
        
        unique_insights = []
        
        for insight in insights:
            is_duplicate = False
            
            for hts:
                similarity = self._calculate_insight_s
                
                if similarity > self.deduplication_threshold:
                    # Keep the insight with higher confiimpact
                    if (insight.confidence_score > existing_insight.confidence_score or
                        insight.business_impact_score > existing_insight.business_e):
                        # Replace existing insight
                        unique_insights.remove(e
                        unique_insights.append(insight)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_insights.append(insight)
        
        return unique_insights
    
    def _correla
        """Find correlations between insights and upda""
        for i, insight1 in enumerate(insights):
            for j, insight2 in enumerate(insights[i+1:], i+1):
                correlation = self._calculate_insight_corrht2)
                
                if correlation > self.cohreshold:
                    insight1.related_insights.appsight2.id)
                    insight2.related_insights.id)
        
        return insights
    
    def _calculate_insight_similarity(
        self, 
        insight1: AggregatedInsight, 
        insight2: Agg
    ) -> float:
        """
        # Same category and similar affected servi
        if insight1.category != insight2.category:
            return 0.0
        
        # Calculate service overlap
        services1 = set(insight1.affected_services)
        services2 = set(insight2.affected_services)
        
        if not services1 or not sees2:
            return 0.0
        
        service_overlap = len(services1.intersection(ses2))
        
        # Calcap)
        ())
        words2 = set(insight2.title.lower().split(
        title_similarity = len(words1.intersection(words2)) / len(words1.union(words2)) if words1.se 0
        
        # Combined similarity
        return (service_overlap * 0.6 + title_similarity * 0.4)
    
    def _calculate_insight_correlation(
        self, 
        insight1: AggregatedIns
        insight2: AggregatedInsight
    ) -> float:
        """Calculate correlation between two insights"""
        # Different categories can be correlated
        correlore = 0.0
        
        # Service overlap corrion
    )
        services2 = set(insight2.affected_srvices)
        
        if services1 and services2:
            service_overlap = 
            correlation_score +=  * 0.4
        
        # Category correlation (some categories naturally correlate)
        category_correlations = {
        .8,
             0.7,
            (InsightCategory.TREND, Insigh.6,
            (InsightCategory.FORECAST, InsightCategory.RECOMMENDATION): 0.5
        }
        
        category_pair = (insight1.categoryy)
        reverse_pair = (insight2.category, insight1.category)
        
        if c
            correlation_score += category_correlat
        elif reverse_pair in category_correlations:
            correlation_score += category_correlations[rev 0.3
        
        # Time correlation (insights from simila
        time_diff = abs((insight1.timestamp - insight2.timestamp).total_seconds
        time_correlation = max(0, 1 - (time_diff / 86400)) on
        corr0.3
        
        return min(correlation_score, 1.0)


clasnker:
    """
    Advanced ple
    criteria including business impact, con
    """
    
    def __init__(self, ranking_wei
        """
        Initialize insight ran
        
        Args:
            ranking_w
        
        self {
            'severity': 0.3,
            'confidence: 0.25,
            'business_impact': 0.25,
            'actionability': 0.2
        }
    
    def rank_insights(
        self, 
        insights: 
        client_context: Optio None
    ) -> List[AggregatedInsight]:
        """
        Rank insice
        
        Args:
            insights: List of aggregated 
            client_context: Client-specific context for ranking
            
        Returns:
            Ranked list of insights
        """
        if not insights:
            return insights
        
        # Calculate ranking scores
        scored_insights = []
        for insight in insights:
            score = self._calculate_ranking_score(insight, client_context
            scored_insights.append((insight, score))
        
        # Sort by score (descending)
        scored_ins=True)
        
        # Update priorities based on ng
        ranks = []
        for i, (insight, scoreghts):
            # Adjust priority based on final ranking
            if i < le 20%
    CAL:
                    insight.priority = InsightPrior
            el0%
                if insight.priorit
                    insight.priority = InsM
            
            ranked_insights.append(insight)
        
        s
    
    def _calculate_ranking_score(
        self, 
        insight: AggregatedInsight,
        Any]]
    ) -> float:
        """Calculate comprehensi"
        
        # Bad 0-1)
        severity_score = insight.severity_score
        confidence_score = insight.confidence_score
        busiscore
        actionability_score = insighe
        
        # Ap
        if client_context:
            # Boost cost optims
            if (client_context.get 
                insight.category inY]):
                business_impact_score =
            
            # Boost capacity planning insights for growing clients
            id
                insight.category == InsightCategory.FORECAST):
            1, 1.0)
            
            # Boost security-related insights for ents
            if (client_context.get('security_focus') and
                'security' in insight.metadata.get('category', '')):
                severity_score = min(severity_score * 1.15, 1.0
        
        # Calculate weighted score
        final_score = (
            severity_score * self.ranking_weights['severity'] +
            confidence_score * self.ranking_weights['confidence'] +
            business_impact_score * self.ranking_weights['business_impact'] +
            ac
        )
        
    ts
        category_boosts = {
            Inurgent
            InsightCategory.RECOMME
            InsightCategory.TREND: 1.,
            InsightCategorygent
            IK: 1.1,
            InsightCategory.OPPORTUNITY: 1.0
        }
        
        final_score *= category_boosts.get(ins.0)
        
        return min(final_score, 1.0)


@dataclass
class Recommendation:y, 1oright.categy.RISghtCategornsiess urts are l# Forecas.95,   0.FORECAST:0nablectio are aationsend # Recomm1.05, : NDATIONomalies are 1,  # An 1.ory.ANOMALY:tegghtCasi booscificegory-spely catpp# A    ity']actionabilhts['ranking_weig self.lity_score *tionabi)ed clirity-focussecu1.core * _sness_impactmin(busie = t_scorss_impac  busine   anling''sca') == _stagerowtht('ggeext.ontent_c(clif .0), 1core * 1.2ss_impact_s(busine mingory.ANOMALCatesightInENDATION, COMMory.REightCateg [Ins andnstraints')get_co('budnt cliestrainedt-con budgesights foration inizntstmext adjuslient conteply c_scorctionabilityt.a_impact_t.business insighe =ormpact_scness_iormalizeady ns (alrese scoreight""or an ins fng scoreve ranki[str, [Dictt: Optionaltexclient_coned_insightreturn rankity.MEDIUightPriorW:riority.LOnsightP == Iy:  # Top 5) * 0.5insightsn(scored_if i < ley.HIGHitRITIriority.CsightPty != In.prioriinsightif             :  # Top * 0.2_insights)n(scoredscored_insinumerate() in ehted_insigrankireversea x: x[1], lambdt(key=s.sorghti)ightsinsnd relevanrtance aby impos ght]] =Any[Dict[str, nalInsight],t[AggregatedLis'hts ornking_weights = raanking_weig.r"""teriaing cri for rankeights Custom ws:eightkerne):loat]] = No, f[Dict[str Optionalghts: urgency.bility, andctionaidence, afultied on msights basizes inhat prioritengine tranking insight tRas Insighrelation * orre += time_cation_scoelti= 0 correla # 1 day ())me periods)r tiair] *_persepair] * 0.3ns[category_ioions:y_correlatr in categorry_paiegoattegor.casight2 in,DATION): 0OMMENgory.RECatetCAST):ory.FOREChtCateg, InsigNDategory.TREnsightC(INDATION): 0gory.RECOMMEsightCateALY, Ingory.ANOMCatesight(In    lapservice_overes2))ervicunion(s(services1.es2)) / lenion(servicectes1.interslen(serviceervicesd_scteight1.affe1 = set(ins    serviceselation_scatight, ds2) elorunion(w))r().splitoweitle.l(insight1.tet = swords1e word overlarity (simplitle similulate ticeon(servuniices1.n(serv / lervices2))rviccesnsightsn two ity betweesimilari"Calculate ""edInsightregat(insight1.appendend(inrelation_tr, insigight1n(inselatiohts"ated_insig reltesight]:egatedIngr-> List[Agight]) Ins[Aggregatedstights: Liself, inss(sightte_inight)ing_insxistcorimpact_sss or businedence ight)xisting_insht, e(insigmilarityique_insigin unig_insight istinex"ilarity"sed on sim insights bate duplicamove"""RetedInsight]:ist[Aggrega Lp=datetime.ustam    time    on_effortmentati': rec.impleon_effortatiicesrv_seec.affected=rvings,ated_sa not problemunities,rt oppoons arecommendati  # Recore=0.5,ity_s  severo Normalize t1.0),  # s / 1000, ted_savingec.estiman(rscore=mi_impact_    business        e,riority.MEDI, InsightPriorityet(rec.pap.grity_miority=prio   pr COMMENDATI.REedInsig Aggregatight =ins.5)rt, 0ion_effoatntemec.impleffortion atementPriority.LOWsight': Inlow{itmendatiocom(renumeratec in ei, rets = [hhts"" insigatedo_insighendations_tvert_recommhtsinsign c         }   ast_perirecrcentage,_pe': changentagege_perce 'chan              urrent_cost,ount': c_am=["all"],servicesffected_      a      ), 30, 1.0entage) /percge_n(abs(chanscore=mi severity_          0.6,0,/ 5nce', 0.5),t('confideast.ge",% change)entage:+.1f}ge_perchant:.2f} ({cunrecast_amo ${focosts:tedExpecf}% Change entage:+.1ge_perc{chant Forecast: title=f"Cos            RECAST,ategory.FOry=InsightCcatego           DIUMrity.MEnsightPrioelse Ie) > 25 rcentagange_peGH if abs(chity.HIchangeant # Significe) > 10:  centagge_per if abs(chan           ) * 10ostt_c currennt_cost) /nt - curreecast_amou((forntage = nt_cost > 0d curreunt > 0 anrecast_amo if font',mou'a.get(_forecastecasts.totalnt = forcast_amouost_daif c]) 0:ta[-3d in cost_dar recorost ford.total_csum(recost = current_cohts"""igted insegagriedCostRecoList[Unifdata:  ForecastReforecasts:ts_to_insicasvert_forensighd(in      },atil: trend.volty'd.grren: twth_rate'        'gro            t25,th_rate) / ow.gr(trend=min(abscoreerity_s   sev ty_scoreabili  action 1) / 40,ateh_rtrend.growtre=min(abs(t_scoess_impacin  bus          .trend_=trendcoreidence_s       conf    te"% rate:.1f}growth_ra} at {trend..valueiontrend.directcosts {ervice} s Trend",ce} Cost{serviriorND,ry.TREgoe_{servie_{i}ervicsatedIty.MEDIriInsightPrio) > 30 else h_raterowts(trend.gaby.HIGH if itghtPriorsity = Inoriri    p    high', 'medivalue in ['ance.signific   if trend.:3ed[_sortvice_trendsnumerate(ser) in erend (service, t,else 0,= 'none' e.value !nificanc1].sigrate) if x[.growth_nds.items(ce_tre.serviendsnt)nifica most sigop 3lit.volati_trendverallds.otren e,_ratnd.growthreoverall_tte': trends.ra],=[ghtsed_insi   relat     ],"all"ervices=[ affected_s      avingsly provide sdon't directnd insights   # Tres=0,mated_saving   esti) / rowth_raterend.gverall_t/ 50, 1.0),rowth_rate) ll_trend.grae}% ratwth_rate:.1fend.groall_trends.overue} at {trction.vald.direll_tren.overa {trendsosts are()}.value.titleectionend.dir.overall_trd: {trendsrenpriority,  priority=y.MEDIUMhtPrioritelse Insig 25 te >h_ra_trend.growtds.overallIGH if trenrity.Hione' != 'noicance.valuell trend insa"""insightstRecord]ostimestmaly.ano  timestamp=d_actionsmendely.recom anomaype.v': anomaly.t=[]tsed_insigh  relatervices,d_s% recoverabme 70 # Assu7, ) * 0.act.cost_impomalyiness_impactore=busce_score,enmaly.confidoon,ti()}", ' ').titlee('_',alue.replacomaly.type.verity.vaomaly.sevtPriority(anInsighriority=     p   ategory.ightCaluepe.v.tyomaly_{an"anomaly_{i}     id=fe, 0.5ity.valualy.sever.get(anomrity_mapeve= srity_score     sevelow': 0. ' 0.6,m':ediu 'm 0.8,h':1.0, 'higrity to scoap seve # Mtions elsed_accommendeanomaly.re= 0.8 if nability actio        ze to $1000mali  # Nor 1.0) 1000,_impact) /y.costbs(anomalin(ampact = mness_i  busi           servicetedt and affecpaccost imbased on  impact business# Calculate             malrate(anoume"nsights"gregated is to agtRecord]osedCnoinsig_to_d_insigrrelateinsightsduplicated_ts(deate_insighelf._correlghts = ssied_inorrelat c       ghts)_insiedgatgrets(ag_insighte._deduplicaghts = selfed_insiuplicat     ded    instion_insigh(recommendandtions(recommendao_insightsns_tast_insighd(forecexten_da, costs(forecastshtto_insigrecasts_rt_fof._conve= selights s to insightecastorrt fend_ixtend(tre_insights.eedgat       aggre
    """Cost optimization recommendation"""
    title: str
    description: str
    estimated_savings: float
    implementation_effort: str  # low, medium, high
    priority: str  # high, medium, low
    category: str  # cost_optimization, security, performance
    affected_services: List[str]
    confidence_score: float
    implementation_steps: List[str]


@dataclass
class AIInsights:
    """Complete AI insights result"""
    executive_summary: str
    anomalies: List[Anomaly]
    trends: TrendAnalysis
    forecasts: ForecastResult
    recommendations: List[Recommendation]
    key_insights: List[str]
    risk_assessment: Dict[str, Any]
    confidence_score: float
    metadata: Dict[str, Any]


class RecommendationEngine:
    """Advanced cost optimization recommendation engine with ML and rule-based approaches"""
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize recommendation engine
        
        Args:
            use_ai: Whether to use AI-powered recommendations
        """
        self.use_ai = use_ai
        
        # Rule-based recommendation templates
        self.rule_based_recommendations = {
            'high_cost_services': {
                'threshold': 1000,
                'template': "Consider optimizing {service} which accounts for ${cost:.2f} ({percentage:.1f}%) of total costs",
                'category': 'cost_optimization',
                'base_priority': 'high',
                'implementation_effort': 'medium'
            },
            'unused_resources': {
                'threshold': 0.1,
                'template': "Review {service} for potential unused resources - low utilization detected",
                'category': 'resource_optimization',
                'base_priority': 'medium',
                'implementation_effort': 'low'
            },
            'cost_spikes': {
                'threshold': 50,
                'template': "Investigate {service} cost spike of {percentage:.1f}% - potential optimization opportunity",
                'category': 'anomaly_resolution',
                'base_priority': 'high',
                'implementation_effort': 'high'
            },
            'budget_overrun': {
                'threshold': 10,
                'template': "Budget overrun detected: {percentage:.1f}% over allocated budget",
                'category': 'budget_management',
                'base_priority': 'critical',
                'implementation_effort': 'medium'
            },
            'seasonal_optimization': {
                'threshold': 20,
                'template': "Seasonal cost pattern detected - consider scaling resources based on {pattern} usage",
                'category': 'seasonal_optimization',
                'base_priority': 'medium',
                'implementation_effort': 'medium'
            },
            'service_consolidation': {
                'threshold': 5,
                'template': "Multiple similar services detected - consider consolidation for {services}",
                'category': 'architecture_optimization',
                'base_priority': 'low',
                'implementation_effort': 'high'
            }
        }
        
        # ML-based recommendation patterns
        self.ml_patterns = {
            'cost_correlation': {
                'description': 'Services with correlated cost patterns',
                'min_correlation': 0.7,
                'recommendation_type': 'optimization'
            },
            'usage_efficiency': {
                'description': 'Services with low cost-to-usage efficiency',
                'efficiency_threshold': 0.3,
                'recommendation_type': 'rightsizing'
            },
            'growth_prediction': {
                'description': 'Services with predicted high growth',
                'growth_threshold': 30,
                'recommendation_type': 'capacity_planning'
            }
        }
        
        # Recommendation scoring weights
        self.scoring_weights = {
            'cost_impact': 0.3,
            'implementation_ease': 0.2,
            'confidence': 0.2,
            'urgency': 0.15,
            'business_impact': 0.15
        }
        
        if use_ai:
            try:
                from .bedrock_service import BedrockService
                self.bedrock_service = BedrockService()
            except Exception as e:
                logger.warning(f"AI service unavailable for recommendations: {e}")
                self.use_ai = False
    
    def generate_recommendations(
        self, 
        cost_data: List[UnifiedCostRecord],
        anomalies: List[Anomaly],
        trends: TrendAnalysis,
        forecasts: ForecastResult,
        client_context: Optional[Dict[str, Any]] = None
    ) -> List[Recommendation]:
        """
        Generate comprehensive cost optimization recommendations using multiple approaches
        
        Args:
            cost_data: Historical cost data
            anomalies: Detected anomalies
            trends: Trend analysis results
            forecasts: Forecast results
            client_context: Additional client context for personalization
            
        Returns:
            List of prioritized recommendations
        """
        recommendations = []
        
        try:
            # 1. Rule-based recommendations
            logger.info("Generating rule-based recommendations")
            rule_recommendations = self._generate_advanced_rule_based_recommendations(
                cost_data, anomalies, trends, forecasts, client_context
            )
            recommendations.extend(rule_recommendations)
            
            # 2. ML-based pattern recommendations
            logger.info("Generating ML-based recommendations")
            ml_recommendations = self._generate_ml_based_recommendations(
                cost_data, trends, forecasts
            )
            recommendations.extend(ml_recommendations)
            
            # 3. Anomaly-driven recommendations
            logger.info("Generating anomaly-based recommendations")
            anomaly_recommendations = self._generate_enhanced_anomaly_recommendations(
                anomalies, cost_data
            )
            recommendations.extend(anomaly_recommendations)
            
            # 4. Trend-driven recommendations
            logger.info("Generating trend-based recommendations")
            trend_recommendations = self._generate_enhanced_trend_recommendations(
                trends, cost_data
            )
            recommendations.extend(trend_recommendations)
            
            # 5. Forecast-driven recommendations
            logger.info("Generating forecast-based recommendations")
            forecast_recommendations = self._generate_enhanced_forecast_recommendations(
                forecasts, cost_data, trends
            )
            recommendations.extend(forecast_recommendations)
            
            # 6. AI-powered recommendations (if available)
            if self.use_ai:
                logger.info("Generating AI-powered recommendations")
                ai_recommendations = self._generate_ai_powered_recommendations(
                    cost_data, anomalies, trends, forecasts, client_context
                )
                recommendations.extend(ai_recommendations)
            
            # 7. Score, deduplicate, and prioritize
            final_recommendations = self._score_and_prioritize_recommendations(
                recommendations, cost_data, client_context
            )
            
            logger.info(f"Generated {len(final_recommendations)} prioritized cost optimization recommendations")
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Advanced recommendation generation failed: {e}")
            return self._generate_fallback_recommendations(cost_data)
    
    def _generate_advanced_rule_based_recommendations(
        self, 
        cost_data: List[UnifiedCostRecord],
        anomalies: List[Anomaly],
        trends: TrendAnalysis,
        forecasts: ForecastResult,
        client_context: Optional[Dict[str, Any]]
    ) -> List[Recommendation]:
        """Generate advanced rule-based recommendations with enhanced logic"""
        recommendations = []
        
        if not cost_data:
            return recommendations
        
        # Analyze service costs and patterns
        service_analysis = self._analyze_service_patterns(cost_data)
        total_cost = sum(record.total_cost for record in cost_data[-30:])
        
        # 1. High cost service optimization
        for service, analysis in service_analysis.items():
            cost = analysis['total_cost']
            percentage = analysis['cost_percentage']
            
            if cost > self.rule_based_recommendations['high_cost_services']['threshold']:
                # Calculate potential savings based on service type and usage patterns
                potential_savings = self._calculate_service_savings_potential(service, analysis)
                
                recommendations.append(Recommendation(
                    title=f"Optimize {service} Costs",
                    description=f"{service} represents {percentage:.1f}% of total costs (${cost:.2f})",
                    estimated_savings=potential_savings,
                    implementation_effort=self._determine_implementation_effort(service, analysis),
                    priority=self._determine_priority(percentage, cost, analysis),
                    category="cost_optimization",
                    affected_services=[service],
                    confidence_score=self._calculate_rule_confidence(analysis),
                    implementation_steps=self._generate_service_optimization_steps(service, analysis)
                ))
        
        # 2. Budget overrun recommendations
        if client_context and 'budget' in client_context:
            budget = client_context['budget']
            if total_cost > budget * 1.1:  # 10% over budget
                overrun_percentage = ((total_cost - budget) / budget) * 100
                
                recommendations.append(Recommendation(
                    title="Address Budget Overrun",
                    description=f"Current spending is {overrun_percentage:.1f}% over allocated budget",
                    estimated_savings=total_cost - budget,
                    implementation_effort="medium",
                    priority="critical",
                    category="budget_management",
                    affected_services=["all"],
                    confidence_score=0.95,
                    implementation_steps=[
                        "Review current month spending patterns",
                        "Identify top cost drivers",
                        "Implement immediate cost controls",
                        "Adjust budget or optimize resources"
                    ]
                ))
        
        # 3. Seasonal optimization recommendations
        seasonal_patterns = self._detect_seasonal_optimization_opportunities(cost_data, trends)
        for pattern in seasonal_patterns:
            recommendations.append(Recommendation(
                title=f"Optimize for {pattern['pattern_type']} Pattern",
                description=pattern['description'],
                estimated_savings=pattern['estimated_savings'],
                implementation_effort="medium",
                priority="medium",
                category="seasonal_optimization",
                affected_services=pattern['affected_services'],
                confidence_score=pattern['confidence'],
                implementation_steps=pattern['implementation_steps']
            ))
        
        # 4. Service consolidation recommendations
        consolidation_opportunities = self._identify_consolidation_opportunities(service_analysis)
        for opportunity in consolidation_opportunities:
            recommendations.append(Recommendation(
                title=f"Consolidate {opportunity['service_group']} Services",
                description=opportunity['description'],
                estimated_savings=opportunity['estimated_savings'],
                implementation_effort="high",
                priority="low",
                category="architecture_optimization",
                affected_services=opportunity['services'],
                confidence_score=opportunity['confidence'],
                implementation_steps=opportunity['implementation_steps']
            ))
        
        return recommendations
    
    def _generate_ml_based_recommendations(
        self,
        cost_data: List[UnifiedCostRecord],
        trends: TrendAnalysis,
        forecasts: ForecastResult
    ) -> List[Recommendation]:
        """Generate ML-based recommendations using pattern analysis"""
        recommendations = []
        
        try:
            # 1. Cost correlation analysis
            correlation_recommendations = self._analyze_cost_correlations(cost_data)
            recommendations.extend(correlation_recommendations)
            
            # 2. Usage efficiency analysis
            efficiency_recommendations = self._analyze_usage_efficiency(cost_data, trends)
            recommendations.extend(efficiency_recommendations)
            
            # 3. Growth prediction recommendations
            growth_recommendations = self._analyze_growth_predictions(cost_data, forecasts)
            recommendations.extend(growth_recommendations)
            
            # 4. Anomaly pattern recommendations
            pattern_recommendations = self._analyze_anomaly_patterns(cost_data)
            recommendations.extend(pattern_recommendations)
            
        except Exception as e:
            logger.error(f"ML-based recommendation generation failed: {e}")
        
        return recommendations
    
    def _generate_ai_powered_recommendations(
        self,
        cost_data: List[UnifiedCostRecord],
        anomalies: List[Anomaly],
        trends: TrendAnalysis,
        forecasts: ForecastResult,
        client_context: Optional[Dict[str, Any]]
    ) -> List[Recommendation]:
        """Generate AI-powered recommendations using LLM"""
        if not self.use_ai:
            return []
        
        try:
            # Prepare context for AI
            context = {
                'cost_summary': self._summarize_costs_for_ai(cost_data),
                'anomalies': [{'type': a.type.value, 'description': a.description, 'impact': a.cost_impact} for a in anomalies[:5]],
                'trends': {
                    'direction': trends.overall_trend.direction.value,
                    'growth_rate': trends.overall_trend.growth_rate,
                    'volatility': trends.overall_trend.volatility
                },
                'forecast': {
                    'total_amount': forecasts.total_forecast.get('amount', 0),
                    'confidence': forecasts.total_forecast.get('confidence', 0)
                }
            }
            
            # Generate AI recommendations
            ai_response = self.bedrock_service.generate_cost_recommendations(context, client_context)
            
            # Parse AI response into Recommendation objects
            ai_recommendations = []
            for rec_data in ai_response.get('recommendations', []):
                ai_recommendations.append(Recommendation(
                    title=rec_data.get('title', 'AI-Generated Recommendation'),
                    description=rec_data.get('description', ''),
                    estimated_savings=rec_data.get('estimated_savings', 0),
                    implementation_effort=rec_data.get('implementation_effort', 'medium'),
                    priority=rec_data.get('priority', 'medium'),
                    category=rec_data.get('category', 'ai_optimization'),
                    affected_services=rec_data.get('affected_services', []),
                    confidence_score=rec_data.get('confidence_score', 0.7),
                    implementation_steps=rec_data.get('implementation_steps', [])
                ))
            
            return ai_recommendations
            
        except Exception as e:
            logger.error(f"AI-powered recommendation generation failed: {e}")
            return []
    
    def _generate_enhanced_anomaly_recommendations(
        self, 
        anomalies: List[Anomaly], 
        cost_data: List[UnifiedCostRecord]
    ) -> List[Recommendation]:
        """Generate enhanced recommendations based on detected anomalies"""
        recommendations = []
        
        # Group anomalies by type for better recommendations
        anomaly_groups = defaultdict(list)
        for anomaly in anomalies:
            anomaly_groups[anomaly.type].append(anomaly)
        
        for anomaly_type, anomaly_list in anomaly_groups.items():
            if not anomaly_list:
                continue
            
            # Get the most severe anomaly in the group
            primary_anomaly = max(anomaly_list, key=lambda a: {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[a.severity.value])
            
            # Calculate total impact
            total_impact = sum(abs(a.cost_impact) for a in anomaly_list)
            
            # Determine recovery potential based on anomaly type
            recovery_rates = {
                'cost_spike': 0.7,
                'new_service': 0.8,
                'unusual_pattern': 0.5,
                'budget_deviation': 0.6,
                'service_disappearance': 0.3  # Lower recovery for disappeared services
            }
            recovery_rate = recovery_rates.get(anomaly_type.value, 0.5)
            
            # Generate comprehensive recommendation
            recommendations.append(Recommendation(
                title=f"Resolve {anomaly_type.value.replace('_', ' ').title()} ({len(anomaly_list)} instances)",
                description=self._generate_anomaly_description(anomaly_type, anomaly_list, total_impact),
                estimated_savings=total_impact * recovery_rate,
                implementation_effort=self._determine_anomaly_effort(primary_anomaly, len(anomaly_list)),
                priority=self._determine_anomaly_priority(primary_anomaly, len(anomaly_list)),
                category="anomaly_resolution",
                affected_services=list(set(service for a in anomaly_list for service in a.affected_services)),
                confidence_score=sum(a.confidence_score for a in anomaly_list) / len(anomaly_list),
                implementation_steps=self._generate_anomaly_resolution_steps(anomaly_type, anomaly_list)
            ))
        
        return recommendations
    
    def _generate_anomaly_description(
        self, 
        anomaly_type: AnomalyType, 
        anomaly_list: List[Anomaly], 
        total_impact: float
    ) -> str:
        """Generate detailed description for anomaly recommendations"""
        count = len(anomaly_list)
        
        if anomaly_type.value == 'cost_spike':
            return f"{count} cost spike(s) detected with total impact of ${total_impact:.2f}. Immediate investigation recommended."
        elif anomaly_type.value == 'new_service':
            services = list(set(service for a in anomaly_list for service in a.affected_services))
            return f"{count} new service(s) detected: {', '.join(services[:3])}{'...' if len(services) > 3 else ''}. Verification needed."
        elif anomaly_type.value == 'budget_deviation':
            return f"Budget deviation detected with ${total_impact:.2f} impact. Cost controls may be needed."
        else:
            return f"{count} {anomaly_type.value.replace('_', ' ')} anomal{'ies' if count > 1 else 'y'} detected requiring attention."
    
    def _determine_anomaly_effort(self, primary_anomaly: Anomaly, count: int) -> str:
        """Determine implementation effort for anomaly resolution"""
        if primary_anomaly.severity.value == 'critical' or count > 3:
            return "high"
        elif primary_anomaly.severity.value == 'high' or count > 1:
            return "medium"
        else:
            return "low"
    
    def _determine_anomaly_priority(self, primary_anomaly: Anomaly, count: int) -> str:
        """Determine priority for anomaly resolution"""
        if primary_anomaly.severity.value == 'critical':
            return "critical"
        elif primary_anomaly.severity.value == 'high' or count > 2:
            return "high"
        else:
            return "medium"
    
    def _generate_anomaly_resolution_steps(
        self, 
        anomaly_type: AnomalyType, 
        anomaly_list: List[Anomaly]
    ) -> List[str]:
        """Generate specific resolution steps for anomaly type"""
        base_steps = [
            "Investigate root cause of anomaly",
            "Verify anomaly is not a false positive",
            "Document findings and resolution"
        ]
        
        if anomaly_type.value == 'cost_spike':
            return [
                "Immediately investigate cost spike causes",
                "Check for configuration changes or scaling events",
                "Review resource utilization patterns",
                "Implement cost alerts to prevent future spikes"
            ] + base_steps
        elif anomaly_type.value == 'new_service':
            return [
                "Verify new service deployments are authorized",
                "Review service configuration and sizing",
                "Ensure proper cost allocation and tagging",
                "Set up monitoring for new services"
            ] + base_steps
        elif anomaly_type.value == 'budget_deviation':
            return [
                "Analyze budget vs actual spending",
                "Identify primary cost drivers",
                "Implement immediate cost controls if needed",
                "Adjust budget or optimize resources"
            ] + base_steps
        else:
            # Combine recommended actions from all anomalies
            all_actions = set()
            for anomaly in anomaly_list:
                all_actions.update(anomaly.recommended_actions)
            return list(all_actions)[:5] + base_steps  # Limit to 5 specific actions
    
    def _generate_enhanced_trend_recommendations(
        self, 
        trends: TrendAnalysis, 
        cost_data: List[UnifiedCostRecord]
    ) -> List[Recommendation]:
        """Generate enhanced recommendations based on trend analysis"""
        recommendations = []
        
        if not cost_data:
            return recommendations
        
        current_total = sum(record.total_cost for record in cost_data[-30:])
        
        # Overall trend recommendations with enhanced logic
        overall_trend = trends.overall_trend
        if overall_trend.significance.value != 'none':
            if overall_trend.direction.value == "increasing" and overall_trend.growth_rate > 15:
                # Calculate potential cost impact
                monthly_impact = current_total * (overall_trend.growth_rate / 100)
                
                recommendations.append(Recommendation(
                    title="Address Accelerating Cost Growth",
                    description=f"Costs increasing at {overall_trend.growth_rate:.1f}% rate with {overall_trend.volatility:.1f}% volatility",
                    estimated_savings=monthly_impact * 0.5,  # Assume we can reduce 50% of growth
                    implementation_effort="medium" if overall_trend.growth_rate < 30 else "high",
                    priority="high" if overall_trend.growth_rate > 25 else "medium",
                    category="trend_management",
                    affected_services=["all"],
                    confidence_score=trends.trend_confidence,
                    implementation_steps=self._generate_growth_control_steps(overall_trend.growth_rate)
                ))
            
            elif overall_trend.direction.value == "decreasing" and abs(overall_trend.growth_rate) > 20:
                # Unexpected cost decrease - might indicate service issues
                recommendations.append(Recommendation(
                    title="Investigate Cost Decrease Trend",
                    description=f"Costs decreasing at {abs(overall_trend.growth_rate):.1f}% rate - verify service availability",
                    estimated_savings=0,  # Investigation recommendation
                    implementation_effort="low",
                    priority="medium",
                    category="trend_investigation",
                    affected_services=["all"],
                    confidence_score=trends.trend_confidence,
                    implementation_steps=[
                        "Verify all services are operational",
                        "Check for service outages or downgrades",
                        "Review usage patterns for anomalies",
                        "Confirm cost decrease is intentional"
                    ]
                ))
        
        # Service-specific trend recommendations with prioritization
        service_trends_sorted = sorted(
            trends.service_trends.items(),
            key=lambda x: (x[1].growth_rate if x[1].direction.value == "increasing" else 0),
            reverse=True
        )
        
        for service, trend in service_trends_sorted[:5]:  # Top 5 growing services
            if (trend.direction.value == "increasing" and 
                trend.growth_rate > 25 and 
                trend.significance.value in ['high', 'medium']):
                
                # Calculate service cost and impact
                service_cost = sum(
                    record.services.get(service, type('obj', (object,), {'cost': 0})).cost 
                    for record in cost_data[-30:]
                )
                growth_impact = service_cost * (trend.growth_rate / 100)
                
                recommendations.append(Recommendation(
                    title=f"Optimize {service} Growth Trajectory",
                    description=f"{service} costs growing at {trend.growth_rate:.1f}% rate (${service_cost:.2f} current)",
                    estimated_savings=growth_impact * 0.6,  # Assume 60% of growth can be optimized
                    implementation_effort=self._determine_service_effort(service, trend),
                    priority=self._determine_service_priority(service, trend, service_cost),
                    category="service_optimization",
                    affected_services=[service],
                    confidence_score=trend.trend_strength,
                    implementation_steps=self._generate_service_trend_steps(service, trend)
                ))
        
        # Volatility-based recommendations
        high_volatility_services = [
            (service, trend) for service, trend in trends.service_trends.items()
            if trend.volatility > 50 and trend.significance.value in ['high', 'medium']
        ]
        
        if high_volatility_services:
            top_volatile = sorted(high_volatility_services, key=lambda x: x[1].volatility, reverse=True)[:3]
            
            for service, trend in top_volatile:
                service_cost = sum(
                    record.services.get(service, type('obj', (object,), {'cost': 0})).cost 
                    for record in cost_data[-30:]
                )
                
                recommendations.append(Recommendation(
                    title=f"Stabilize {service} Cost Patterns",
                    description=f"{service} shows high cost volatility ({trend.volatility:.1f}%) indicating inefficient usage",
                    estimated_savings=service_cost * 0.15,  # 15% savings from stabilization
                    implementation_effort="medium",
                    priority="medium",
                    category="volatility_optimization",
                    affected_services=[service],
                    confidence_score=min(trend.volatility / 100, 1.0),
                    implementation_steps=[
                        f"Analyze {service} usage patterns and triggers",
                        "Implement predictive scaling policies",
                        "Set up cost monitoring and alerts",
                        "Consider reserved capacity for stable workloads"
                    ]
                ))
        
        return recommendations
    
    def _generate_growth_control_steps(self, growth_rate: float) -> List[str]:
        """Generate steps to control cost growth"""
        if growth_rate > 30:
            return [
                "Immediate cost analysis and freeze on new resources",
                "Review all recent deployments and scaling events",
                "Implement emergency cost controls and alerts",
                "Conduct comprehensive cost optimization review",
                "Set up automated cost monitoring and governance"
            ]
        else:
            return [
                "Implement proactive cost monitoring and alerts",
                "Review resource scaling policies and thresholds",
                "Conduct regular cost optimization reviews",
                "Set up budget controls and approval processes",
                "Monitor growth trends and adjust strategies"
            ]
    
    def _determine_service_effort(self, service: str, trend: TrendMetrics) -> str:
        """Determine implementation effort for service optimization"""
        if trend.growth_rate > 50 or trend.volatility > 70:
            return "high"
        elif trend.growth_rate > 30 or trend.volatility > 40:
            return "medium"
        else:
            return "low"
    
    def _determine_service_priority(self, service: str, trend: TrendMetrics, service_cost: float) -> str:
        """Determine priority for service optimization"""
        if trend.growth_rate > 40 or service_cost > 2000:
            return "high"
        elif trend.growth_rate > 25 or service_cost > 1000:
            return "medium"
        else:
            return "low"
    
    def _generate_service_trend_steps(self, service: str, trend: TrendMetrics) -> List[str]:
        """Generate service-specific trend optimization steps"""
        steps = [
            f"Analyze {service} usage patterns and growth drivers",
            f"Review {service} resource allocation and sizing"
        ]
        
        if trend.volatility > 40:
            steps.append(f"Implement auto-scaling for {service} to handle usage variations")
        
        if trend.growth_rate > 35:
            steps.extend([
                f"Investigate root cause of {service} cost growth",
                f"Consider reserved capacity or savings plans for {service}"
            ])
        
        # Add service-specific recommendations
        if 'compute' in service.lower() or 'ec2' in service.lower():
            steps.extend([
                "Review instance types and consider rightsizing",
                "Evaluate spot instances for non-critical workloads"
            ])
        elif 'storage' in service.lower() or 's3' in service.lower():
            steps.extend([
                "Review storage classes and lifecycle policies",
                "Implement intelligent tiering and archiving"
            ])
        elif 'database' in service.lower() or 'rds' in service.lower():
            steps.extend([
                "Optimize database performance and queries",
                "Consider read replicas and caching strategies"
            ])
        
        steps.append(f"Monitor {service} optimization impact and adjust as needed")
        return steps
    
    def _generate_enhanced_forecast_recommendations(
        self, 
        forecasts: ForecastResult, 
        cost_data: List[UnifiedCostRecord],
        trends: TrendAnalysis
    ) -> List[Recommendation]:
        """Generate enhanced recommendations based on forecast results"""
        recommendations = []
        
        if not cost_data or forecasts.accuracy_assessment.value == 'very_low':
            return recommendations
        
        current_total = sum(record.total_cost for record in cost_data[-30:])
        forecast_amount = forecasts.total_forecast.get('amount', 0)
        forecast_confidence = forecasts.total_forecast.get('confidence', 0)
        
        if forecast_amount > 0 and forecast_confidence > 0.3:
            # Calculate forecast vs current comparison
            forecast_change = ((forecast_amount - current_total) / current_total * 100) if current_total > 0 else 0
            
            # Budget planning recommendation
            if forecasts.accuracy_assessment.value in ['high', 'medium']:
                recommendations.append(Recommendation(
                    title="Strategic Budget Planning Based on Forecast",
                    description=f"Forecasted costs for next {forecasts.forecast_period}: ${forecast_amount:.2f} ({forecast_change:+.1f}% change)",
                    estimated_savings=0,  # Planning tool
                    implementation_effort="low",
                    priority="medium" if abs(forecast_change) > 10 else "low",
                    category="budget_planning",
                    affected_services=["all"],
                    confidence_score=forecast_confidence,
                    implementation_steps=self._generate_budget_planning_steps(forecast_change, forecasts)
                ))
            
            # Capacity planning for significant growth
            if forecast_change > 20:
                recommendations.append(Recommendation(
                    title="Prepare for Forecasted Cost Growth",
                    description=f"Forecast indicates {forecast_change:.1f}% cost increase - capacity planning needed",
                    estimated_savings=forecast_amount * 0.1,  # 10% savings through proactive planning
                    implementation_effort="medium",
                    priority="high" if forecast_change > 40 else "medium",
                    category="capacity_planning",
                    affected_services=["all"],
                    confidence_score=forecast_confidence,
                    implementation_steps=[
                        "Analyze forecast growth drivers and assumptions",
                        "Plan infrastructure capacity and scaling",
                        "Consider reserved instance purchases",
                        "Implement proactive cost monitoring",
                        "Prepare budget adjustments and approvals"
                    ]
                ))
            
            # Cost reduction opportunity for declining forecasts
            elif forecast_change < -15:
                recommendations.append(Recommendation(
                    title="Investigate Forecasted Cost Decline",
                    description=f"Forecast shows {abs(forecast_change):.1f}% cost decrease - verify assumptions",
                    estimated_savings=0,  # Investigation recommendation
                    implementation_effort="low",
                    priority="medium",
                    category="forecast_validation",
                    affected_services=["all"],
                    confidence_score=forecast_confidence,
                    implementation_steps=[
                        "Verify forecast assumptions and methodology",
                        "Check for planned service reductions or optimizations",
                        "Ensure forecast accounts for business requirements",
                        "Validate with actual usage trends"
                    ]
                ))
            
            # Seasonal planning recommendations
            if hasattr(forecasts, 'seasonal_insights') and forecasts.seasonal_insights:
                recommendations.append(Recommendation(
                    title="Optimize for Seasonal Cost Patterns",
                    description="Forecast indicates seasonal cost variations - optimize resource allocation",
                    estimated_savings=current_total * 0.08,  # 8% savings from seasonal optimization
                    implementation_effort="medium",
                    priority="medium",
                    category="seasonal_optimization",
                    affected_services=["all"],
                    confidence_score=forecast_confidence * 0.8,  # Slightly lower confidence for seasonal
                    implementation_steps=[
                        "Analyze seasonal cost patterns in forecast",
                        "Plan resource scaling for peak and off-peak periods",
                        "Implement automated seasonal adjustments",
                        "Set up seasonal budget allocations"
                    ]
                ))
            
            # Risk mitigation for high uncertainty
            variance_range = forecasts.total_forecast.get('variance_range', {})
            if variance_range:
                max_variance = variance_range.get('max', forecast_amount)
                min_variance = variance_range.get('min', forecast_amount)
                uncertainty = ((max_variance - min_variance) / forecast_amount * 100) if forecast_amount > 0 else 0
                
                if uncertainty > 30:  # High uncertainty
                    recommendations.append(Recommendation(
                        title="Mitigate Forecast Uncertainty Risk",
                        description=f"High forecast uncertainty ({uncertainty:.1f}% variance) - implement risk controls",
                        estimated_savings=0,  # Risk mitigation
                        implementation_effort="medium",
                        priority="medium",
                        category="risk_management",
                        affected_services=["all"],
                        confidence_score=1.0 - (uncertainty / 100),
                        implementation_steps=[
                            "Implement flexible budgeting with contingency reserves",
                            "Set up early warning cost monitoring",
                            "Prepare cost control measures for different scenarios",
                            "Review and improve forecasting data quality"
                        ]
                    ))
        
        return recommendations
    
    def _generate_budget_planning_steps(self, forecast_change: float, forecasts: ForecastResult) -> List[str]:
        """Generate budget planning steps based on forecast"""
        steps = ["Review current budget allocations and assumptions"]
        
        if forecast_change > 15:
            steps.extend([
                "Prepare budget increase justification and approval",
                "Identify cost optimization opportunities to offset growth",
                "Set up enhanced cost monitoring and alerts"
            ])
        elif forecast_change < -10:
            steps.extend([
                "Verify forecast assumptions and business requirements",
                "Consider budget reallocation opportunities",
                "Plan for potential service level adjustments"
            ])
        else:
            steps.extend([
                "Adjust budget based on forecast trends",
                "Set up proactive cost monitoring"
            ])
        
        # Add seasonal planning if applicable
        if 'seasonal' in forecasts.assumptions:
            steps.append("Plan for seasonal cost variations")
        
        steps.extend([
            "Communicate forecast and budget changes to stakeholders",
            "Set up regular forecast vs actual reviews"
        ])
        
        return steps
    
    def _analyze_service_patterns(self, cost_data: List[UnifiedCostRecord]) -> Dict[str, Dict[str, Any]]:
        """Analyze service cost patterns and characteristics"""
        service_analysis = defaultdict(lambda: {
            'total_cost': 0,
            'daily_costs': [],
            'cost_percentage': 0,
            'volatility': 0,
            'trend': 'stable',
            'usage_pattern': 'consistent'
        })
        
        total_cost = 0
        
        # Collect service data
        for record in cost_data[-30:]:  # Last 30 days
            total_cost += record.total_cost
            for service, cost_info in record.services.items():
                service_analysis[service]['total_cost'] += cost_info.cost
                service_analysis[service]['daily_costs'].append(cost_info.cost)
        
        # Calculate patterns for each service
        for service, analysis in service_analysis.items():
            analysis['cost_percentage'] = (analysis['total_cost'] / total_cost * 100) if total_cost > 0 else 0
            
            daily_costs = analysis['daily_costs']
            if len(daily_costs) > 1:
                mean_cost = statistics.mean(daily_costs)
                analysis['volatility'] = (statistics.stdev(daily_costs) / mean_cost * 100) if mean_cost > 0 else 0
                
                # Simple trend detection
                if len(daily_costs) >= 7:
                    recent_avg = statistics.mean(daily_costs[-7:])
                    older_avg = statistics.mean(daily_costs[:-7]) if len(daily_costs) > 7 else mean_cost
                    
                    if recent_avg > older_avg * 1.1:
                        analysis['trend'] = 'increasing'
                    elif recent_avg < older_avg * 0.9:
                        analysis['trend'] = 'decreasing'
                
                # Usage pattern detection
                if analysis['volatility'] > 50:
                    analysis['usage_pattern'] = 'volatile'
                elif analysis['volatility'] < 10:
                    analysis['usage_pattern'] = 'stable'
                else:
                    analysis['usage_pattern'] = 'moderate'
        
        return dict(service_analysis)
    
    def _calculate_service_savings_potential(self, service: str, analysis: Dict[str, Any]) -> float:
        """Calculate potential savings for a service based on its characteristics"""
        base_cost = analysis['total_cost']
        
        # Base savings potential
        savings_rate = 0.10  # 10% base
        
        # Adjust based on volatility (high volatility = more optimization potential)
        if analysis['volatility'] > 50:
            savings_rate += 0.10
        elif analysis['volatility'] > 30:
            savings_rate += 0.05
        
        # Adjust based on trend
        if analysis['trend'] == 'increasing':
            savings_rate += 0.05
        
        # Adjust based on service type (heuristic)
        if 'compute' in service.lower() or 'ec2' in service.lower():
            savings_rate += 0.05  # Compute services often have more optimization potential
        elif 'storage' in service.lower() or 's3' in service.lower():
            savings_rate += 0.03  # Storage optimization potential
        
        return base_cost * min(savings_rate, 0.30)  # Cap at 30% savings
    
    def _determine_implementation_effort(self, service: str, analysis: Dict[str, Any]) -> str:
        """Determine implementation effort based on service characteristics"""
        if analysis['cost_percentage'] > 50:
            return "high"  # High-impact services require more careful planning
        elif analysis['volatility'] > 50:
            return "medium"  # Volatile services need analysis
        else:
            return "low"
    
    def _determine_priority(self, percentage: float, cost: float, analysis: Dict[str, Any]) -> str:
        """Determine recommendation priority"""
        if percentage > 40 or cost > 5000:
            return "high"
        elif percentage > 20 or cost > 2000:
            return "medium"
        else:
            return "low"
    
    def _calculate_rule_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for rule-based recommendations"""
        confidence = 0.7  # Base confidence
        
        # Higher confidence for stable patterns
        if analysis['usage_pattern'] == 'stable':
            confidence += 0.1
        elif analysis['usage_pattern'] == 'volatile':
            confidence -= 0.1
        
        # Higher confidence for clear trends
        if analysis['trend'] in ['increasing', 'decreasing']:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_service_optimization_steps(self, service: str, analysis: Dict[str, Any]) -> List[str]:
        """Generate service-specific optimization steps"""
        steps = [
            f"Analyze {service} usage patterns and resource utilization",
            f"Review {service} configuration and sizing"
        ]
        
        if analysis['volatility'] > 30:
            steps.append("Implement auto-scaling to handle usage variations")
        
        if analysis['trend'] == 'increasing':
            steps.append("Investigate root cause of cost growth")
            steps.append("Consider reserved capacity or savings plans")
        
        if 'compute' in service.lower():
            steps.extend([
                "Review instance types and sizes",
                "Consider spot instances for non-critical workloads"
            ])
        elif 'storage' in service.lower():
            steps.extend([
                "Review storage classes and lifecycle policies",
                "Implement data archiving strategies"
            ])
        
        steps.append("Monitor optimization impact and adjust as needed")
        return steps
    
    def _detect_seasonal_optimization_opportunities(
        self, 
        cost_data: List[UnifiedCostRecord], 
        trends: TrendAnalysis
    ) -> List[Dict[str, Any]]:
        """Detect seasonal patterns that could be optimized"""
        opportunities = []
        
        if trends.seasonal_patterns.seasonal_strength > 0.3:
            pattern_type = trends.seasonal_patterns.seasonal_pattern.value
            
            opportunities.append({
                'pattern_type': pattern_type,
                'description': f"Strong {pattern_type} seasonal pattern detected with potential for resource scaling",
                'estimated_savings': sum(record.total_cost for record in cost_data[-30:]) * 0.15,
                'affected_services': ['compute', 'storage'],
                'confidence': trends.seasonal_patterns.seasonal_strength,
                'implementation_steps': [
                    f"Analyze {pattern_type} usage patterns",
                    "Implement predictive scaling policies",
                    "Consider scheduled resource adjustments",
                    "Monitor seasonal cost variations"
                ]
            })
        
        return opportunities
    
    def _identify_consolidation_opportunities(self, service_analysis: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify service consolidation opportunities"""
        opportunities = []
        
        # Group similar services
        service_groups = defaultdict(list)
        for service, analysis in service_analysis.items():
            # Simple grouping by service type
            if 'compute' in service.lower() or 'ec2' in service.lower():
                service_groups['compute'].append((service, analysis))
            elif 'storage' in service.lower() or 's3' in service.lower():
                service_groups['storage'].append((service, analysis))
            elif 'database' in service.lower() or 'rds' in service.lower():
                service_groups['database'].append((service, analysis))
        
        # Look for consolidation opportunities
        for group_name, services in service_groups.items():
            if len(services) >= 3:  # Multiple services of same type
                total_cost = sum(analysis['total_cost'] for _, analysis in services)
                service_names = [service for service, _ in services]
                
                opportunities.append({
                    'service_group': group_name,
                    'description': f"Multiple {group_name} services detected - consolidation may reduce costs",
                    'estimated_savings': total_cost * 0.10,  # 10% savings from consolidation
                    'services': service_names,
                    'confidence': 0.6,
                    'implementation_steps': [
                        f"Analyze {group_name} service usage overlap",
                        "Evaluate consolidation feasibility",
                        "Plan migration strategy",
                        "Implement gradual consolidation"
                    ]
                })
        
        return opportunities
    
    def _analyze_cost_correlations(self, cost_data: List[UnifiedCostRecord]) -> List[Recommendation]:
        """Analyze cost correlations between services"""
        recommendations = []
        
        # This is a simplified correlation analysis
        # In a real implementation, you'd use proper statistical correlation
        
        service_costs_by_day = defaultdict(list)
        
        for record in cost_data[-30:]:
            for service, cost_info in record.services.items():
                service_costs_by_day[service].append(cost_info.cost)
        
        # Find services with similar cost patterns (simplified)
        services = list(service_costs_by_day.keys())
        for i, service1 in enumerate(services):
            for service2 in services[i+1:]:
                costs1 = service_costs_by_day[service1]
                costs2 = service_costs_by_day[service2]
                
                if len(costs1) == len(costs2) and len(costs1) > 7:
                    # Simple correlation check (would use proper correlation in real implementation)
                    correlation = self._simple_correlation(costs1, costs2)
                    
                    if correlation > 0.7:
                        total_cost = sum(costs1) + sum(costs2)
                        recommendations.append(Recommendation(
                            title=f"Optimize Correlated Services: {service1} and {service2}",
                            description=f"Services show high cost correlation ({correlation:.2f}) - potential for joint optimization",
                            estimated_savings=total_cost * 0.08,
                            implementation_effort="medium",
                            priority="medium",
                            category="correlation_optimization",
                            affected_services=[service1, service2],
                            confidence_score=correlation,
                            implementation_steps=[
                                "Analyze service interdependencies",
                                "Optimize shared resources",
                                "Consider joint scaling policies"
                            ]
                        ))
        
        return recommendations
    
    def _simple_correlation(self, costs1: List[float], costs2: List[float]) -> float:
        """Simple correlation calculation"""
        if len(costs1) != len(costs2) or len(costs1) < 2:
            return 0.0
        
        mean1 = statistics.mean(costs1)
        mean2 = statistics.mean(costs2)
        
        numerator = sum((c1 - mean1) * (c2 - mean2) for c1, c2 in zip(costs1, costs2))
        
        sum_sq1 = sum((c1 - mean1) ** 2 for c1 in costs1)
        sum_sq2 = sum((c2 - mean2) ** 2 for c2 in costs2)
        
        denominator = math.sqrt(sum_sq1 * sum_sq2)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def _analyze_usage_efficiency(self, cost_data: List[UnifiedCostRecord], trends: TrendAnalysis) -> List[Recommendation]:
        """Analyze usage efficiency patterns"""
        recommendations = []
        
        # Simplified efficiency analysis based on cost volatility and trends
        for service, trend in trends.service_trends.items():
            if trend.volatility > 60:  # High volatility suggests inefficient usage
                service_cost = sum(
                    record.services.get(service, type('obj', (object,), {'cost': 0})).cost 
                    for record in cost_data[-30:]
                )
                
                recommendations.append(Recommendation(
                    title=f"Improve {service} Usage Efficiency",
                    description=f"{service} shows high cost volatility ({trend.volatility:.1f}%) indicating inefficient usage",
                    estimated_savings=service_cost * 0.20,
                    implementation_effort="medium",
                    priority="medium",
                    category="efficiency_optimization",
                    affected_services=[service],
                    confidence_score=min(trend.volatility / 100, 1.0),
                    implementation_steps=[
                        f"Analyze {service} usage patterns",
                        "Implement usage monitoring and alerts",
                        "Optimize resource allocation",
                        "Consider usage-based scaling"
                    ]
                ))
        
        return recommendations
    
    def _analyze_growth_predictions(self, cost_data: List[UnifiedCostRecord], forecasts: ForecastResult) -> List[Recommendation]:
        """Analyze growth predictions for capacity planning"""
        recommendations = []
        
        if forecasts.accuracy_assessment.value in ['high', 'medium']:
            forecast_amount = forecasts.total_forecast.get('amount', 0)
            current_amount = sum(record.total_cost for record in cost_data[-30:])
            
            if forecast_amount > current_amount * 1.2:  # 20% growth predicted
                growth_rate = ((forecast_amount - current_amount) / current_amount) * 100
                
                recommendations.append(Recommendation(
                    title="Plan for Predicted Cost Growth",
                    description=f"Forecast indicates {growth_rate:.1f}% cost growth - proactive planning recommended",
                    estimated_savings=0,  # This is a planning recommendation
                    implementation_effort="low",
                    priority="medium",
                    category="capacity_planning",
                    affected_services=["all"],
                    confidence_score=forecasts.total_forecast.get('confidence', 0.5),
                    implementation_steps=[
                        "Review growth drivers and assumptions",
                        "Plan capacity and budget adjustments",
                        "Consider reserved capacity purchases",
                        "Implement proactive monitoring"
                    ]
                ))
        
        return recommendations
    
    def _analyze_anomaly_patterns(self, cost_data: List[UnifiedCostRecord]) -> List[Recommendation]:
        """Analyze patterns in cost data that might indicate optimization opportunities"""
        recommendations = []
        
        # Look for recurring patterns that might indicate inefficiencies
        # This is a simplified analysis - real implementation would be more sophisticated
        
        daily_costs = [record.total_cost for record in cost_data[-30:]]
        if len(daily_costs) >= 7:
            weekly_patterns = []
            for i in range(0, len(daily_costs) - 6, 7):
                week_costs = daily_costs[i:i+7]
                weekly_patterns.append(sum(week_costs))
            
            if len(weekly_patterns) >= 3:
                weekly_volatility = statistics.stdev(weekly_patterns) / statistics.mean(weekly_patterns) * 100
                
                if weekly_volatility > 30:
                    recommendations.append(Recommendation(
                        title="Optimize Weekly Cost Patterns",
                        description=f"High weekly cost variation ({weekly_volatility:.1f}%) suggests optimization opportunities",
                        estimated_savings=sum(daily_costs) * 0.10,
                        implementation_effort="medium",
                        priority="medium",
                        category="pattern_optimization",
                        affected_services=["all"],
                        confidence_score=0.6,
                        implementation_steps=[
                            "Analyze weekly usage patterns",
                            "Identify cost variation drivers",
                            "Implement workload scheduling",
                            "Consider time-based scaling"
                        ]
                    ))
        
        return recommendations
    
    def _summarize_costs_for_ai(self, cost_data: List[UnifiedCostRecord]) -> Dict[str, Any]:
        """Summarize cost data for AI analysis"""
        if not cost_data:
            return {}
        
        total_cost = sum(record.total_cost for record in cost_data[-30:])
        service_costs = defaultdict(float)
        
        for record in cost_data[-30:]:
            for service, cost_info in record.services.items():
                service_costs[service] += cost_info.cost
        
        # Get top services
        top_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_cost_30_days': total_cost,
            'average_daily_cost': total_cost / min(30, len(cost_data)),
            'top_services': [{'service': service, 'cost': cost, 'percentage': cost/total_cost*100} for service, cost in top_services],
            'data_points': len(cost_data),
            'date_range': {
                'start': cost_data[0].date,
                'end': cost_data[-1].date
            }
        }
    
    def _generate_fallback_recommendations(self, cost_data: List[UnifiedCostRecord]) -> List[Recommendation]:
        """Generate basic fallback recommendations when advanced methods fail"""
        if not cost_data:
            return []
        
        total_cost = sum(record.total_cost for record in cost_data[-30:])
        
        return [
            Recommendation(
                title="Review Cost Optimization Opportunities",
                description=f"Current 30-day costs: ${total_cost:.2f} - general optimization review recommended",
                estimated_savings=total_cost * 0.10,
                implementation_effort="medium",
                priority="medium",
                category="general_optimization",
                affected_services=["all"],
                confidence_score=0.5,
                implementation_steps=[
                    "Review resource utilization",
                    "Identify unused resources",
                    "Consider cost optimization tools",
                    "Implement monitoring and alerts"
                ]
            )
        ]
    
    def _score_and_prioritize_recommendations(
        self, 
        recommendations: List[Recommendation], 
        cost_data: List[UnifiedCostRecord],
        client_context: Optional[Dict[str, Any]]
    ) -> List[Recommendation]:
        """Advanced scoring and prioritization of recommendations"""
        if not recommendations:
            return []
        
        # 1. Remove duplicates based on similarity
        unique_recommendations = self._deduplicate_recommendations(recommendations)
        
        # 2. Calculate comprehensive scores
        scored_recommendations = []
        total_cost = sum(record.total_cost for record in cost_data[-30:]) if cost_data else 1
        
        for rec in unique_recommendations:
            score = self._calculate_recommendation_score(rec, total_cost, client_context)
            scored_recommendations.append((rec, score))
        
        # 3. Sort by score
        scored_recommendations.sort(key=lambda x: x[1], reverse=True)
        
        # 4. Update priorities based on scores
        final_recommendations = []
        for i, (rec, score) in enumerate(scored_recommendations[:15]):  # Top 15
            # Update priority based on final score
            if score > 0.8:
                rec.priority = "critical"
            elif score > 0.6:
                rec.priority = "high"
            elif score > 0.4:
                rec.priority = "medium"
            else:
                rec.priority = "low"
            
            final_recommendations.append(rec)
        
        logger.info(f"Prioritized {len(final_recommendations)} recommendations with advanced scoring")
        return final_recommendations
    
    def _deduplicate_recommendations(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """Remove duplicate recommendations based on similarity"""
        unique_recommendations = []
        seen_combinations = set()
        
        for rec in recommendations:
            # Create a key based on affected services and category
            key = (tuple(sorted(rec.affected_services)), rec.category)
            
            if key not in seen_combinations:
                unique_recommendations.append(rec)
                seen_combinations.add(key)
            else:
                # If duplicate, keep the one with higher confidence or savings
                for i, existing_rec in enumerate(unique_recommendations):
                    existing_key = (tuple(sorted(existing_rec.affected_services)), existing_rec.category)
                    if existing_key == key:
                        if (rec.confidence_score > existing_rec.confidence_score or 
                            rec.estimated_savings > existing_rec.estimated_savings):
                            unique_recommendations[i] = rec
                        break
        
        return unique_recommendations
    
    def _calculate_recommendation_score(
        self, 
        rec: Recommendation, 
        total_cost: float,
        client_context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate comprehensive recommendation score"""
        
        # Cost impact score (0-1)
        cost_impact_score = min(rec.estimated_savings / (total_cost * 0.1), 1.0)  # Normalize to 10% of total cost
        
        # Implementation ease score (0-1)
        effort_scores = {'low': 1.0, 'medium': 0.7, 'high': 0.4}
        implementation_ease_score = effort_scores.get(rec.implementation_effort, 0.5)
        
        # Confidence score (already 0-1)
        confidence_score = rec.confidence_score
        
        # Urgency score based on category and priority (0-1)
        urgency_score = self._calculate_urgency_score(rec)
        
        # Business impact score (0-1)
        business_impact_score = self._calculate_business_impact_score(rec, client_context)
        
        # Calculate weighted score
        final_score = (
            cost_impact_score * self.scoring_weights['cost_impact'] +
            implementation_ease_score * self.scoring_weights['implementation_ease'] +
            confidence_score * self.scoring_weights['confidence'] +
            urgency_score * self.scoring_weights['urgency'] +
            business_impact_score * self.scoring_weights['business_impact']
        )
        
        return min(final_score, 1.0)
    
    def _calculate_urgency_score(self, rec: Recommendation) -> float:
        """Calculate urgency score based on category and priority"""
        priority_scores = {'critical': 1.0, 'high': 0.8, 'medium': 0.5, 'low': 0.2}
        base_score = priority_scores.get(rec.priority, 0.5)
        
        # Boost score for certain categories
        if rec.category in ['budget_management', 'anomaly_resolution']:
            base_score += 0.2
        elif rec.category in ['cost_optimization', 'efficiency_optimization']:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_business_impact_score(
        self, 
        rec: Recommendation, 
        client_context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate business impact score"""
        base_score = 0.5
        
        # Higher impact for recommendations affecting multiple services
        if len(rec.affected_services) > 3:
            base_score += 0.2
        elif len(rec.affected_services) > 1:
            base_score += 0.1
        
        # Higher impact for certain categories
        if rec.category in ['budget_management', 'capacity_planning']:
            base_score += 0.2
        elif rec.category in ['cost_optimization', 'seasonal_optimization']:
            base_score += 0.1
        
        # Consider client context if available
        if client_context:
            if 'budget_constraints' in client_context and client_context['budget_constraints']:
                if rec.category in ['budget_management', 'cost_optimization']:
                    base_score += 0.1
            
            if 'growth_stage' in client_context and client_context['growth_stage'] == 'scaling':
                if rec.category in ['capacity_planning', 'architecture_optimization']:
                    base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _prioritize_recommendations(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """Legacy method - delegates to new scoring system"""
        return self._score_and_prioritize_recommendations(recommendations, [], None)


class AIInsightsService:
    """
    Main AI insights orchestration service with comprehensive workflow management
    
    This service acts as the central orchestrator for all AI-powered cost analysis,
    coordinating anomaly detection, trend analysis, forecasting, and recommendation
    generation with advanced insight aggregation and ranking capabilities.
    """
    
    def __init__(self, use_ai: bool = True):
        """
        Initialize AI insights service with enhanced orchestration capabilities
        
        Args:
            use_ai: Whether to use AI-powered analysis
        """
        self.use_ai = use_ai
        
        # Core AI analysis engines
        self.anomaly_detector = AnomalyDetectionEngine(use_ai=use_ai)
        self.trend_analyzer = TrendAnalyzer()
        self.forecasting_engine = ForecastingEngine(use_ai=use_ai)
        self.recommendation_engine = RecommendationEngine(use_ai=use_ai)
        
        # Enhanced workflow orchestration components
        self.workflow_state = {}
        self.insight_cache = {}
        self.processing_queue = []
        self.workflow_metrics = {}
        
        # Insight aggregation and ranking components
        self.insight_aggregator = InsightAggregator()
        self.insight_ranker = InsightRanker()
        
        # Workflow configuration
        self.workflow_config = {
            'parallel_processing': True,
            'cache_enabled': True,
            'quality_threshold': 0.7,
            'max_insights_per_category': 10,
            'insight_ranking_weights': {
                'severity': 0.3,
                'confidence': 0.25,
                'business_impact': 0.25,
                'actionability': 0.2
            }
        }
        
        if use_ai:
            try:
                self.bedrock_service = BedrockService()
            except Exception as e:
                logger.warning(f"AI service unavailable: {e}")
                self.use_ai = False
    
    def orchestrate_insights_workflow(
        self, 
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig] = None,
        budget_info: Optional[Dict[str, float]] = None,
        workflow_options: Optional[Dict[str, Any]] = None
    ) -> AIInsights:
        """
        Orchestrate comprehensive AI insights workflow with advanced orchestration
        
        Args:
            client_id: Client identifier
            cost_data: Historical cost data
            client_config: Client configuration
            budget_info: Budget information
            workflow_options: Workflow configuration options
            
        Returns:
            Complete AI insights with orchestration metadata
        """
        workflow_id = f"{client_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Initialize workflow state
            self.workflow_state[workflow_id] = {
                'client_id': client_id,
                'status': 'initializing',
                'start_time': datetime.utcnow(),
                'steps_completed': [],
                'steps_failed': [],
                'current_step': None
            }
            
            # Check cache for recent insights
            cache_key = self._generate_cache_key(client_id, cost_data)
            if cache_key in self.insight_cache:
                cached_insights = self.insight_cache[cache_key]
                if self._is_cache_valid(cached_insights):
                    logger.info(f"Returning cached insights for client {client_id}")
                    return cached_insights
            
            # Execute orchestrated workflow
            insights = self._execute_insights_workflow(
                workflow_id, client_id, cost_data, client_config, budget_info, workflow_options
            )
            
            # Cache results
            self.insight_cache[cache_key] = insights
            
            # Update workflow state
            self.workflow_state[workflow_id]['status'] = 'completed'
            self.workflow_state[workflow_id]['end_time'] = datetime.utcnow()
            
            return insights
            
        except Exception as e:
            logger.error(f"AI insights workflow failed for client {client_id}: {e}")
            self.workflow_state[workflow_id]['status'] = 'failed'
            self.workflow_state[workflow_id]['error'] = str(e)
            return self._get_minimal_insights(client_id, cost_data)
    
    def _execute_insights_workflow(
        self,
        workflow_id: str,
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig],
        budget_info: Optional[Dict[str, float]],
        workflow_options: Optional[Dict[str, Any]]
    ) -> AIInsights:
        """Execute the complete insights workflow with orchestration"""
        
        workflow_steps = [
            ('data_validation', self._validate_workflow_data),
            ('anomaly_detection', self._execute_anomaly_detection),
            ('trend_analysis', self._execute_trend_analysis),
            ('forecasting', self._execute_forecasting),
            ('recommendation_generation', self._execute_recommendation_generation),
            ('insight_aggregation', self._execute_insight_aggregation),
            ('narrative_generation', self._execute_narrative_generation),
            ('quality_assessment', self._execute_quality_assessment)
        ]
        
        workflow_results = {}
        
        for step_name, step_function in workflow_steps:
            try:
                self.workflow_state[workflow_id]['current_step'] = step_name
                logger.info(f"Executing workflow step: {step_name} for client {client_id}")
                
                step_result = step_function(
                    client_id, cost_data, client_config, budget_info, workflow_results
                )
                
                workflow_results[step_name] = step_result
                self.workflow_state[workflow_id]['steps_completed'].append(step_name)
                
            except Exception as e:
                logger.error(f"Workflow step {step_name} failed for client {client_id}: {e}")
                self.workflow_state[workflow_id]['steps_failed'].append({
                    'step': step_name,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Continue with degraded functionality
                workflow_results[step_name] = self._get_fallback_result(step_name)
        
        # Compile final insights
        return self._compile_workflow_insights(workflow_id, workflow_results, client_id)
    
    def _validate_workflow_data(
        self,
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig],
        budget_info: Optional[Dict[str, float]],
        workflow_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate input data for workflow"""
        validation_result = {
            'data_quality_score': 0.0,
            'data_completeness': 0.0,
            'data_freshness': 0.0,
            'validation_warnings': [],
            'validation_errors': []
        }
        
        if not cost_data:
            validation_result['validation_errors'].append("No cost data provided")
            return validation_result
        
        # Data completeness check
        total_records = len(cost_data)
        complete_records = sum(1 for record in cost_data if record.total_cost > 0)
        validation_result['data_completeness'] = complete_records / total_records if total_records > 0 else 0
        
        # Data freshness check
        if cost_data:
            latest_date = max(datetime.fromisoformat(record.date) for record in cost_data)
            days_old = (datetime.utcnow() - latest_date).days
            validation_result['data_freshness'] = max(0, 1 - (days_old / 30))  # 30 days = 0 freshness
        
        # Data quality assessment
        if len(cost_data) >= 7:
            validation_result['data_quality_score'] = min(
                validation_result['data_completeness'] + validation_result['data_freshness'], 1.0
            )
        else:
            validation_result['validation_warnings'].append("Insufficient data for comprehensive analysis")
        
        return validation_result
    
    def _execute_anomaly_detection(
        self,
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig],
        budget_info: Optional[Dict[str, float]],
        workflow_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute anomaly detection step"""
        if len(cost_data) < 7:
            return {'anomalies': [], 'detection_confidence': 0.0}
        
        historical_data = cost_data[:-7] if len(cost_data) > 14 else cost_data[:-1]
        current_data = cost_data[-7:] if len(cost_data) > 14 else cost_data[-1:]
        
        anomalies = self.anomaly_detector.detect_anomalies(
            current_data, historical_data, budget_info
        )
        
        # Calculate detection confidence
        detection_confidence = 0.0
        if anomalies:
            detection_confidence = sum(a.confidence_score for a in anomalies) / len(anomalies)
        
        return {
            'anomalies': anomalies,
            'detection_confidence': detection_confidence,
            'anomaly_count': len(anomalies),
            'critical_anomalies': len([a for a in anomalies if a.severity.value == 'critical'])
        }
    
    def _execute_trend_analysis(
        self,
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig],
        budget_info: Optional[Dict[str, float]],
        workflow_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute trend analysis step"""
        trends = self.trend_analyzer.analyze_trends(cost_data)
        
        return {
            'trends': trends,
            'trend_confidence': trends.trend_confidence,
            'overall_direction': trends.overall_trend.direction.value,
            'growth_rate': trends.overall_trend.growth_rate,
            'volatility': trends.overall_trend.volatility
        }
    
    def _execute_forecasting(
        self,
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig],
        budget_info: Optional[Dict[str, float]],
        workflow_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute forecasting step"""
        forecasts = self.forecasting_engine.generate_forecast(cost_data, forecast_horizon=30)
        
        return {
            'forecasts': forecasts,
            'forecast_accuracy': forecasts.accuracy_assessment.value,
            'total_forecast_amount': forecasts.total_forecast.get('amount', 0),
            'forecast_confidence': forecasts.total_forecast.get('confidence', 0)
        }
    
    def _execute_recommendation_generation(
        self,
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig],
        budget_info: Optional[Dict[str, float]],
        workflow_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute recommendation generation step"""
        anomalies = workflow_results.get('anomaly_detection', {}).get('anomalies', [])
        trends = workflow_results.get('trend_analysis', {}).get('trends')
        forecasts = workflow_results.get('forecasting', {}).get('forecasts')
        
        if not all([trends, forecasts]):
            return {'recommendations': [], 'recommendation_confidence': 0.0}
        
        recommendations = self.recommendation_engine.generate_recommendations(
            cost_data, anomalies, trends, forecasts
        )
        
        # Calculate recommendation confidence
        recommendation_confidence = 0.0
        if recommendations:
            recommendation_confidence = sum(r.confidence_score for r in recommendations) / len(recommendations)
        
        return {
            'recommendations': recommendations,
            'recommendation_confidence': recommendation_confidence,
            'high_priority_recommendations': len([r for r in recommendations if r.priority == 'high']),
            'estimated_total_savings': sum(r.estimated_savings for r in recommendations)
        }
    
    def _execute_insight_aggregation(
        self,
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig],
        budget_info: Optional[Dict[str, float]],
        workflow_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute enhanced insight aggregation and ranking step using new components"""
        
        try:
            # Extract results from workflow steps
            anomalies = workflow_results.get('anomaly_detection', {}).get('anomalies', [])
            trends = workflow_results.get('trend_analysis', {}).get('trends')
            forecasts = workflow_results.get('forecasting', {}).get('forecasts')
            recommendations = workflow_results.get('recommendation_generation', {}).get('recommendations', [])
            
            # Use enhanced insight aggregator
            aggregated_insights = self.insight_aggregator.aggregate_insights(
                anomalies=anomalies,
                trends=trends,
                forecasts=forecasts,
                recommendations=recommendations,
                cost_data=cost_data
            )
            
            # Prepare client context for ranking
            client_context = {}
            if client_config:
                client_context.update({
                    'budget_constraints': getattr(client_config, 'budget_constraints', False),
                    'growth_stage': getattr(client_config, 'growth_stage', 'stable'),
                    'security_focus': getattr(client_config, 'security_focus', False)
                })
            
            if budget_info:
                current_cost = sum(record.total_cost for record in cost_data[-30:]) if cost_data else 0
                total_budget = sum(budget_info.values()) if budget_info else 0
                if total_budget > 0:
                    client_context['budget_utilization'] = current_cost / total_budget
                    client_context['budget_constraints'] = current_cost > total_budget * 0.8
            
            # Use enhanced insight ranker
            ranked_insights = self.insight_ranker.rank_insights(
                insights=aggregated_insights,
                client_context=client_context
            )
            
            # Organize insights by category and priority
            insights_by_category = defaultdict(list)
            insights_by_priority = defaultdict(list)
            
            for insight in ranked_insights:
                insights_by_category[insight.category.value].append(insight)
                insights_by_priority[insight.priority.value].append(insight)
            
            # Calculate aggregation metrics
            total_estimated_savings = sum(insight.estimated_savings for insight in ranked_insights)
            avg_confidence = sum(insight.confidence_score for insight in ranked_insights) / len(ranked_insights) if ranked_insights else 0
            
            return {
                'aggregated_insights': ranked_insights,
                'insights_by_category': dict(insights_by_category),
                'insights_by_priority': dict(insights_by_priority),
                'total_insights': len(ranked_insights),
                'critical_insights': len(insights_by_priority.get('critical', [])),
                'high_priority_insights': len(insights_by_priority.get('high', [])),
                'total_estimated_savings': total_estimated_savings,
                'average_confidence': avg_confidence,
                'aggregation_metadata': {
                    'aggregation_timestamp': datetime.utcnow().isoformat(),
                    'client_context_applied': bool(client_context),
                    'deduplication_applied': True,
                    'correlation_analysis_applied': True
                }
            }
            
        except Exception as e:
            logger.error(f"Enhanced insight aggregation failed: {e}")
            # Fallback to basic aggregation
            return self._execute_basic_insight_aggregation(workflow_results)
    
    def _execute_basic_insight_aggregation(self, workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback basic insight aggregation"""
        aggregated_insights = {
            'key_insights': [],
            'priority_insights': [],
            'actionable_insights': [],
            'insight_categories': defaultdict(list)
        }
        
        # Extract insights from anomalies
        anomalies = workflow_results.get('anomaly_detection', {}).get('anomalies', [])
        for anomaly in anomalies[:3]:
            insight = f"{anomaly.type.value.replace('_', ' ').title()}: {anomaly.description}"
            aggregated_insights['key_insights'].append(insight)
            aggregated_insights['insight_categories']['anomalies'].append(insight)
            
            if anomaly.severity.value in ['critical', 'high']:
                aggregated_insights['priority_insights'].append(insight)
        
        # Extract insights from trends
        trends = workflow_results.get('trend_analysis', {}).get('trends')
        if trends and hasattr(trends, 'key_insights'):
            aggregated_insights['key_insights'].extend(trends.key_insights[:3])
            aggregated_insights['insight_categories']['trends'].extend(trends.key_insights)
        
        # Extract insights from recommendations
        recommendations = workflow_results.get('recommendation_generation', {}).get('recommendations', [])
        for rec in recommendations[:3]:
            insight = f"Recommendation: {rec.title} (Est. savings: ${rec.estimated_savings:.0f})"
            aggregated_insights['actionable_insights'].append(insight)
            aggregated_insights['insight_categories']['recommendations'].append(insight)
        
        return aggregated_insights
    
    def _execute_narrative_generation(
        self,
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig],
        budget_info: Optional[Dict[str, float]],
        workflow_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute narrative generation step"""
        
        # Generate executive summary
        executive_summary = self._generate_comprehensive_executive_summary(
            cost_data, workflow_results, client_config
        )
        
        # Generate detailed narrative
        detailed_narrative = self._generate_detailed_narrative(
            cost_data, workflow_results, client_config
        )
        
        return {
            'executive_summary': executive_summary,
            'detailed_narrative': detailed_narrative,
            'narrative_confidence': 0.8  # High confidence in narrative generation
        }
    
    def _execute_quality_assessment(
        self,
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig],
        budget_info: Optional[Dict[str, float]],
        workflow_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute quality assessment of insights"""
        
        quality_metrics = {
            'overall_confidence': 0.0,
            'data_quality': workflow_results.get('data_validation', {}).get('data_quality_score', 0.0),
            'analysis_completeness': 0.0,
            'insight_reliability': 0.0,
            'actionability_score': 0.0
        }
        
        # Calculate analysis completeness
        completed_steps = len([step for step in workflow_results.keys() if workflow_results[step]])
        total_steps = 8  # Total workflow steps
        quality_metrics['analysis_completeness'] = completed_steps / total_steps
        
        # Calculate insight reliability
        confidence_scores = []
        if 'anomaly_detection' in workflow_results:
            confidence_scores.append(workflow_results['anomaly_detection'].get('detection_confidence', 0))
        if 'trend_analysis' in workflow_results:
            confidence_scores.append(workflow_results['trend_analysis'].get('trend_confidence', 0))
        if 'forecasting' in workflow_results:
            confidence_scores.append(workflow_results['forecasting'].get('forecast_confidence', 0))
        
        if confidence_scores:
            quality_metrics['insight_reliability'] = sum(confidence_scores) / len(confidence_scores)
        
        # Calculate actionability score
        recommendations = workflow_results.get('recommendation_generation', {}).get('recommendations', [])
        if recommendations:
            actionable_recs = len([r for r in recommendations if r.implementation_effort in ['low', 'medium']])
            quality_metrics['actionability_score'] = actionable_recs / len(recommendations)
        
        # Calculate overall confidence
        quality_metrics['overall_confidence'] = sum([
            quality_metrics['data_quality'] * 0.3,
            quality_metrics['analysis_completeness'] * 0.2,
            quality_metrics['insight_reliability'] * 0.3,
            quality_metrics['actionability_score'] * 0.2
        ])
        
        return quality_metrics

    def generate_insights(
        self, 
        client_id: str,
        cost_data: List[UnifiedCostRecord],
        client_config: Optional[ClientConfig] = None,
        budget_info: Optional[Dict[str, float]] = None
    ) -> AIInsights:
        """
        Generate comprehensive AI insights for cost data (legacy method - uses orchestration)
        
        Args:
            client_id: Client identifier
            cost_data: Historical cost data
            client_config: Client configuration
            budget_info: Budget information
            
        Returns:
            Complete AI insights
        """
        # Delegate to the new orchestration workflow
        return self.orchestrate_insights_workflow(
            client_id=client_id,
            cost_data=cost_data,
            client_config=client_config,
            budget_info=budget_info,
            workflow_options=None
        )
    
    def _generate_executive_summary(
        self, 
        cost_data: List[UnifiedCostRecord],
        anomalies: List[Anomaly],
        trends: TrendAnalysis,
        forecasts: ForecastResult,
        client_config: Optional[ClientConfig]
    ) -> tuple[str, List[str]]:
        """Generate executive summary and key insights"""
        
        if not cost_data:
            return "No cost data available for analysis.", []
        
        # Calculate basic metrics
        total_cost = sum(record.total_cost for record in cost_data[-30:])  # Last 30 days
        avg_daily_cost = total_cost / min(30, len(cost_data))
        
        # Build executive summary
        summary_parts = []
        
        # Cost overview
        summary_parts.append(f"Total costs over the last {min(30, len(cost_data))} days: ${total_cost:,.2f}")
        summary_parts.append(f"Average daily cost: ${avg_daily_cost:,.2f}")
        
        # Trend information
        if trends.overall_trend.significance.value != 'none':
            trend_direction = trends.overall_trend.direction.value
            growth_rate = abs(trends.overall_trend.growth_rate)
            summary_parts.append(f"Cost trend is {trend_direction} at {growth_rate:.1f}% rate")
        
        # Anomaly information
        critical_anomalies = [a for a in anomalies if a.severity.value == 'critical']
        if critical_anomalies:
            summary_parts.append(f"{len(critical_anomalies)} critical cost anomalies detected")
        
        # Forecast information
        if forecasts.accuracy_assessment.value in ['high', 'medium']:
            forecast_amount = forecasts.total_forecast.get('amount', 0)
            summary_parts.append(f"Forecasted costs for next 30 days: ${forecast_amount:,.2f}")
        
        executive_summary = ". ".join(summary_parts) + "."
        
        # Generate key insights
        key_insights = []
        
        # Add trend insights
        key_insights.extend(trends.key_insights[:3])  # Top 3 trend insights
        
        # Add anomaly insights
        for anomaly in anomalies[:2]:  # Top 2 anomalies
            key_insights.append(f"{anomaly.type.value.replace('_', ' ').title()}: {anomaly.description}")
        
        # Add forecast insights
        if forecasts.assumptions:
            key_insights.append(f"Forecast based on: {forecasts.assumptions[0]}")
        
        return executive_summary, key_insights[:5]  # Limit to 5 key insights
    
    def _assess_risks(
        self, 
        anomalies: List[Anomaly], 
        trends: TrendAnalysis, 
        forecasts: ForecastResult
    ) -> Dict[str, Any]:
        """Assess various risk factors"""
        
        risk_assessment = {
            'overall_risk_level': 'low',
            'risk_factors': [],
            'risk_score': 0.0,
            'mitigation_recommendations': []
        }
        
        risk_score = 0.0
        
        # Anomaly-based risks
        critical_anomalies = [a for a in anomalies if a.severity.value == 'critical']
        high_anomalies = [a for a in anomalies if a.severity.value == 'high']
        
        if critical_anomalies:
            risk_score += 0.4
            risk_assessment['risk_factors'].append(f"{len(critical_anomalies)} critical anomalies detected")
            risk_assessment['mitigation_recommendations'].append("Immediate investigation of critical anomalies required")
        
        if high_anomalies:
            risk_score += 0.2
            risk_assessment['risk_factors'].append(f"{len(high_anomalies)} high-severity anomalies detected")
        
        # Trend-based risks
        if trends.overall_trend.direction.value == "increasing" and trends.overall_trend.growth_rate > 30:
            risk_score += 0.3
            risk_assessment['risk_factors'].append("Rapid cost growth trend detected")
            risk_assessment['mitigation_recommendations'].append("Implement cost controls and monitoring")
        
        if trends.overall_trend.volatility > 50:
            risk_score += 0.2
            risk_assessment['risk_factors'].append("High cost volatility detected")
            risk_assessment['mitigation_recommendations'].append("Stabilize cost patterns through better resource management")
        
        # Forecast-based risks
        if forecasts.accuracy_assessment.value == 'very_low':
            risk_score += 0.1
            risk_assessment['risk_factors'].append("Low forecast accuracy - unpredictable costs")
            risk_assessment['mitigation_recommendations'].append("Improve cost monitoring and data collection")
        
        # Determine overall risk level
        if risk_score >= 0.7:
            risk_assessment['overall_risk_level'] = 'critical'
        elif risk_score >= 0.5:
            risk_assessment['overall_risk_level'] = 'high'
        elif risk_score >= 0.3:
            risk_assessment['overall_risk_level'] = 'medium'
        else:
            risk_assessment['overall_risk_level'] = 'low'
        
        risk_assessment['risk_score'] = min(risk_score, 1.0)
        
        return risk_assessment
    
    def _calculate_overall_confidence(
        self, 
        anomalies: List[Anomaly], 
        trends: TrendAnalysis, 
        forecasts: ForecastResult,
        data_points: int
    ) -> float:
        """Calculate overall confidence in the analysis"""
        
        confidence_factors = []
        
        # Data sufficiency factor
        data_confidence = min(data_points / 30, 1.0)  # 30 days = 100% confidence
        confidence_factors.append(data_confidence)
        
        # Trend analysis confidence
        confidence_factors.append(trends.trend_confidence)
        
        # Forecast confidence
        forecast_confidence = forecasts.total_forecast.get('confidence', 0.5)
        confidence_factors.append(forecast_confidence)
        
        # Anomaly detection confidence
        if anomalies:
            anomaly_confidence = sum(a.confidence_score for a in anomalies) / len(anomalies)
            confidence_factors.append(anomaly_confidence)
        else:
            confidence_factors.append(0.7)  # No anomalies is moderately confident
        
        # AI availability factor
        if self.use_ai:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.6)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _generate_cache_key(self, client_id: str, cost_data: List[UnifiedCostRecord]) -> str:
        """Generate cache key for insights"""
        if not cost_data:
            return f"{client_id}_empty"
        
        # Use client ID, data range, and data hash
        start_date = min(record.date for record in cost_data)
        end_date = max(record.date for record in cost_data)
        data_hash = hash(tuple(record.total_cost for record in cost_data[-10:]))  # Last 10 records
        
        return f"{client_id}_{start_date}_{end_date}_{data_hash}"
    
    def _is_cache_valid(self, cached_insights: AIInsights, max_age_hours: int = 6) -> bool:
        """Check if cached insights are still valid"""
        if not hasattr(cached_insights, 'metadata') or not cached_insights.metadata:
            return False
        
        cache_time_str = cached_insights.metadata.get('analysis_timestamp')
        if not cache_time_str:
            return False
        
        try:
            cache_time = datetime.fromisoformat(cache_time_str.replace('Z', '+00:00'))
            age_hours = (datetime.utcnow() - cache_time.replace(tzinfo=None)).total_seconds() / 3600
            return age_hours < max_age_hours
        except Exception:
            return False
    
    def _get_fallback_result(self, step_name: str) -> Dict[str, Any]:
        """Get fallback result for failed workflow step"""
        fallback_results = {
            'data_validation': {
                'data_quality_score': 0.5,
                'data_completeness': 0.5,
                'data_freshness': 0.5,
                'validation_warnings': ['Step failed - using fallback'],
                'validation_errors': []
            },
            'anomaly_detection': {
                'anomalies': [],
                'detection_confidence': 0.0,
                'anomaly_count': 0,
                'critical_anomalies': 0
            },
            'trend_analysis': {
                'trends': self.trend_analyzer._get_default_analysis(),
                'trend_confidence': 0.0,
                'overall_direction': 'stable',
                'growth_rate': 0.0,
                'volatility': 0.0
            },
            'forecasting': {
                'forecasts': self.forecasting_engine._get_minimal_forecast([], 30),
                'forecast_accuracy': 'very_low',
                'total_forecast_amount': 0,
                'forecast_confidence': 0.0
            },
            'recommendation_generation': {
                'recommendations': [],
                'recommendation_confidence': 0.0,
                'high_priority_recommendations': 0,
                'estimated_total_savings': 0
            },
            'insight_aggregation': {
                'key_insights': ['Analysis step failed'],
                'priority_insights': [],
                'actionable_insights': [],
                'insight_categories': defaultdict(list),
                'ranked_insights': []
            },
            'narrative_generation': {
                'executive_summary': 'Analysis unavailable due to processing error',
                'detailed_narrative': 'Detailed analysis could not be completed',
                'narrative_confidence': 0.0
            },
            'quality_assessment': {
                'overall_confidence': 0.0,
                'data_quality': 0.0,
                'analysis_completeness': 0.0,
                'insight_reliability': 0.0,
                'actionability_score': 0.0
            }
        }
        
        return fallback_results.get(step_name, {})
    
    def _rank_insights(self, insights: List[str]) -> List[Dict[str, Any]]:
        """Rank insights by importance and actionability"""
        ranked = []
        
        for i, insight in enumerate(insights):
            # Simple ranking based on keywords and position
            importance_score = 1.0 - (i * 0.1)  # Earlier insights are more important
            
            # Boost score for critical keywords
            if any(keyword in insight.lower() for keyword in ['critical', 'urgent', 'immediate']):
                importance_score += 0.3
            elif any(keyword in insight.lower() for keyword in ['high', 'significant', 'major']):
                importance_score += 0.2
            elif any(keyword in insight.lower() for keyword in ['recommendation', 'savings', 'optimize']):
                importance_score += 0.1
            
            ranked.append({
                'insight': insight,
                'importance_score': min(importance_score, 1.0),
                'category': self._categorize_insight(insight)
            })
        
        # Sort by importance score
        ranked.sort(key=lambda x: x['importance_score'], reverse=True)
        return ranked[:10]  # Top 10 insights
    
    def _categorize_insight(self, insight: str) -> str:
        """Categorize insight by type"""
        insight_lower = insight.lower()
        
        if 'anomaly' in insight_lower or 'spike' in insight_lower or 'unusual' in insight_lower:
            return 'anomaly'
        elif 'trend' in insight_lower or 'growth' in insight_lower or 'increasing' in insight_lower:
            return 'trend'
        elif 'recommendation' in insight_lower or 'optimize' in insight_lower or 'savings' in insight_lower:
            return 'recommendation'
        elif 'forecast' in insight_lower or 'predict' in insight_lower:
            return 'forecast'
        else:
            return 'general'
    
    def _generate_comprehensive_executive_summary(
        self,
        cost_data: List[UnifiedCostRecord],
        workflow_results: Dict[str, Any],
        client_config: Optional[ClientConfig]
    ) -> str:
        """Generate comprehensive executive summary"""
        
        if not cost_data:
            return "No cost data available for analysis."
        
        # Basic metrics
        total_cost = sum(record.total_cost for record in cost_data[-30:])  # Last 30 days
        avg_daily_cost = total_cost / min(30, len(cost_data))
        
        summary_parts = []
        
        # Cost overview
        summary_parts.append(f"Total costs over the last {min(30, len(cost_data))} days: ${total_cost:,.2f}")
        summary_parts.append(f"Average daily cost: ${avg_daily_cost:,.2f}")
        
        # Trend information
        trend_results = workflow_results.get('trend_analysis', {})
        if trend_results.get('trends'):
            trends = trend_results['trends']
            if trends.overall_trend.significance.value != 'none':
                direction = trends.overall_trend.direction.value
                growth_rate = abs(trends.overall_trend.growth_rate)
                summary_parts.append(f"Cost trend is {direction} at {growth_rate:.1f}% rate")
        
        # Anomaly information
        anomaly_results = workflow_results.get('anomaly_detection', {})
        critical_anomalies = anomaly_results.get('critical_anomalies', 0)
        if critical_anomalies > 0:
            summary_parts.append(f"{critical_anomalies} critical cost anomalies detected requiring immediate attention")
        
        # Forecast information
        forecast_results = workflow_results.get('forecasting', {})
        if forecast_results.get('forecast_accuracy') in ['high', 'medium']:
            forecast_amount = forecast_results.get('total_forecast_amount', 0)
            summary_parts.append(f"Forecasted costs for next 30 days: ${forecast_amount:,.2f}")
        
        # Recommendations
        rec_results = workflow_results.get('recommendation_generation', {})
        estimated_savings = rec_results.get('estimated_total_savings', 0)
        if estimated_savings > 0:
            summary_parts.append(f"Potential cost savings identified: ${estimated_savings:,.2f}")
        
        # Quality assessment
        quality_results = workflow_results.get('quality_assessment', {})
        overall_confidence = quality_results.get('overall_confidence', 0)
        confidence_text = "high" if overall_confidence > 0.7 else "medium" if overall_confidence > 0.4 else "low"
        summary_parts.append(f"Analysis confidence: {confidence_text}")
        
        return ". ".join(summary_parts) + "."
    
    def _generate_detailed_narrative(
        self,
        cost_data: List[UnifiedCostRecord],
        workflow_results: Dict[str, Any],
        client_config: Optional[ClientConfig]
    ) -> str:
        """Generate detailed narrative of the analysis"""
        
        narrative_parts = []
        
        # Data quality section
        validation_results = workflow_results.get('data_validation', {})
        data_quality = validation_results.get('data_quality_score', 0)
        narrative_parts.append(f"Data Quality Assessment: {data_quality:.1%} quality score based on completeness and freshness.")
        
        # Anomaly section
        anomaly_results = workflow_results.get('anomaly_detection', {})
        anomaly_count = anomaly_results.get('anomaly_count', 0)
        if anomaly_count > 0:
            narrative_parts.append(f"Anomaly Detection: {anomaly_count} anomalies detected in recent cost patterns.")
        else:
            narrative_parts.append("Anomaly Detection: No significant anomalies detected in recent cost patterns.")
        
        # Trend section
        trend_results = workflow_results.get('trend_analysis', {})
        if trend_results.get('trends'):
            direction = trend_results.get('overall_direction', 'stable')
            growth_rate = trend_results.get('growth_rate', 0)
            volatility = trend_results.get('volatility', 0)
            narrative_parts.append(f"Trend Analysis: Overall cost trend is {direction} with {abs(growth_rate):.1f}% growth rate and {volatility:.1f}% volatility.")
        
        # Forecast section
        forecast_results = workflow_results.get('forecasting', {})
        forecast_accuracy = forecast_results.get('forecast_accuracy', 'low')
        narrative_parts.append(f"Forecasting: Cost predictions generated with {forecast_accuracy} accuracy level.")
        
        # Recommendations section
        rec_results = workflow_results.get('recommendation_generation', {})
        rec_count = len(rec_results.get('recommendations', []))
        high_priority = rec_results.get('high_priority_recommendations', 0)
        if rec_count > 0:
            narrative_parts.append(f"Recommendations: {rec_count} optimization recommendations generated, including {high_priority} high-priority items.")
        
        return " ".join(narrative_parts)
    
    def _compile_workflow_insights(
        self,
        workflow_id: str,
        workflow_results: Dict[str, Any],
        client_id: str
    ) -> AIInsights:
        """Compile final insights from workflow results with enhanced aggregation"""
        
        # Extract components from workflow results
        anomalies = workflow_results.get('anomaly_detection', {}).get('anomalies', [])
        trends = workflow_results.get('trend_analysis', {}).get('trends', self.trend_analyzer._get_default_analysis())
        forecasts = workflow_results.get('forecasting', {}).get('forecasts', self.forecasting_engine._get_minimal_forecast([], 30))
        recommendations = workflow_results.get('recommendation_generation', {}).get('recommendations', [])
        
        # Get enhanced aggregated insights
        insight_aggregation = workflow_results.get('insight_aggregation', {})
        aggregated_insights = insight_aggregation.get('aggregated_insights', [])
        insights_by_priority = insight_aggregation.get('insights_by_priority', {})
        
        # Extract key insights from aggregated insights
        key_insights = []
        if aggregated_insights:
            # Get top insights from each category
            for insight in aggregated_insights[:10]:  # Top 10 insights
                key_insights.append(f"{insight.title}: {insight.description}")
        else:
            # Fallback to basic key insights
            key_insights = insight_aggregation.get('key_insights', [])
        
        # Get narrative
        narrative_results = workflow_results.get('narrative_generation', {})
        executive_summary = narrative_results.get('executive_summary', 'Analysis completed')
        
        # Get quality assessment
        quality_results = workflow_results.get('quality_assessment', {})
        overall_confidence = quality_results.get('overall_confidence', 0.5)
        
        # Enhanced risk assessment using aggregated insights
        risk_assessment = self._assess_enhanced_risks(
            anomalies, trends, forecasts, aggregated_insights
        )
        
        # Calculate enhanced metadata
        enhanced_metadata = {
            'client_id': client_id,
            'workflow_id': workflow_id,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'workflow_state': self.workflow_state.get(workflow_id, {}),
            'orchestration_enabled': True,
            'quality_metrics': quality_results,
            'aggregation_metrics': {
                'total_insights': len(aggregated_insights),
                'critical_insights': len(insights_by_priority.get('critical', [])),
                'high_priority_insights': len(insights_by_priority.get('high', [])),
                'total_estimated_savings': insight_aggregation.get('total_estimated_savings', 0),
                'average_confidence': insight_aggregation.get('average_confidence', 0)
            },
            'workflow_performance': {
                'steps_completed': len(self.workflow_state.get(workflow_id, {}).get('steps_completed', [])),
                'steps_failed': len(self.workflow_state.get(workflow_id, {}).get('steps_failed', [])),
                'processing_time': self._calculate_processing_time(workflow_id)
            }
        }
        
        # Compile final insights
        insights = AIInsights(
            executive_summary=executive_summary,
            anomalies=anomalies,
            trends=trends,
            forecasts=forecasts,
            recommendations=recommendations,
            key_insights=key_insights,
            risk_assessment=risk_assessment,
            confidence_score=overall_confidence,
            metadata=enhanced_metadata
        )
        
        return insights
    
    def _assess_enhanced_risks(
        self,
        anomalies: List[Anomaly],
        trends: TrendAnalysis,
        forecasts: ForecastResult,
        aggregated_insights: List[AggregatedInsight]
    ) -> Dict[str, Any]:
        """Enhanced risk assessment using aggregated insights"""
        
        risk_assessment = {
            'overall_risk_level': 'low',
            'risk_factors': [],
            'risk_score': 0.0,
            'critical_risks': [],
            'mitigation_recommendations': []
        }
        
        risk_score = 0.0
        
        # Assess risks from aggregated insights
        critical_insights = [i for i in aggregated_insights if i.priority == InsightPriority.CRITICAL]
        high_priority_insights = [i for i in aggregated_insights if i.priority == InsightPriority.HIGH]
        
        if critical_insights:
            risk_score += 0.4
            risk_assessment['critical_risks'].extend([i.title for i in critical_insights])
            risk_assessment['risk_factors'].append(f"{len(critical_insights)} critical insights detected")
        
        if high_priority_insights:
            risk_score += 0.2
            risk_assessment['risk_factors'].append(f"{len(high_priority_insights)} high priority insights detected")
        
        # Assess anomaly risks
        critical_anomalies = [a for a in anomalies if a.severity.value == 'critical']
        if critical_anomalies:
            risk_score += 0.3
            risk_assessment['risk_factors'].append(f"{len(critical_anomalies)} critical anomalies")
        
        # Assess trend risks
        if trends.overall_trend.growth_rate > 30:
            risk_score += 0.2
            risk_assessment['risk_factors'].append(f"High cost growth rate: {trends.overall_trend.growth_rate:.1f}%")
        
        # Assess forecast risks
        if forecasts.accuracy_assessment.value in ['high', 'medium']:
            forecast_amount = forecasts.total_forecast.get('amount', 0)
            if forecast_amount > 0:
                # Assume current cost for comparison
                current_cost = 1000  # This would be calculated from cost_data in real implementation
                if forecast_amount > current_cost * 1.5:  # 50% increase
                    risk_score += 0.15
                    risk_assessment['risk_factors'].append("Significant cost increase forecasted")
        
        # Determine overall risk level
        if risk_score >= 0.7:
            risk_assessment['overall_risk_level'] = 'critical'
        elif risk_score >= 0.5:
            risk_assessment['overall_risk_level'] = 'high'
        elif risk_score >= 0.3:
            risk_assessment['overall_risk_level'] = 'medium'
        
        risk_assessment['risk_score'] = min(risk_score, 1.0)
        
        # Generate mitigation recommendations
        if risk_score > 0.5:
            risk_assessment['mitigation_recommendations'].extend([
                "Implement immediate cost monitoring and alerts",
                "Review and optimize high-cost services",
                "Establish emergency cost control procedures"
            ])
        elif risk_score > 0.3:
            risk_assessment['mitigation_recommendations'].extend([
                "Enhance cost monitoring and reporting",
                "Conduct regular cost optimization reviews"
            ])
        
        return risk_assessment
    
    def _calculate_processing_time(self, workflow_id: str) -> float:
        """Calculate workflow processing time in seconds"""
        workflow_state = self.workflow_state.get(workflow_id, {})
        start_time = workflow_state.get('start_time')
        end_time = workflow_state.get('end_time', datetime.utcnow())
        
        if start_time:
            return (end_time - start_time).total_seconds()
        return 0.0

    def _get_minimal_insights(
        self, 
        client_id: str, 
        cost_data: List[UnifiedCostRecord]
    ) -> AIInsights:
        """Generate minimal insights for insufficient data"""
        
        if not cost_data:
            total_cost = 0
            summary = "No cost data available for analysis."
        else:
            total_cost = sum(record.total_cost for record in cost_data)
            summary = f"Limited analysis available. Total costs: ${total_cost:,.2f} over {len(cost_data)} days."
        
        return AIInsights(
            executive_summary=summary,
            anomalies=[],
            trends=self.trend_analyzer._get_default_analysis(),
            forecasts=self.forecasting_engine._get_minimal_forecast(cost_data, 30),
            recommendations=[],
            key_insights=["Insufficient data for comprehensive analysis"],
            risk_assessment={
                'overall_risk_level': 'unknown',
                'risk_factors': ['Insufficient data'],
                'risk_score': 0.0,
                'mitigation_recommendations': ['Collect more historical data']
            },
            confidence_score=0.1,
            metadata={
                'client_id': client_id,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'data_points_analyzed': len(cost_data),
                'insufficient_data': True
            }
        )
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow"""
        return self.workflow_state.get(workflow_id)
    
    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows"""
        active_workflows = []
        for workflow_id, state in self.workflow_state.items():
            if state.get('status') in ['initializing', 'running']:
                active_workflows.append({
                    'workflow_id': workflow_id,
                    'client_id': state.get('client_id'),
                    'status': state.get('status'),
                    'current_step': state.get('current_step'),
                    'start_time': state.get('start_time'),
                    'steps_completed': len(state.get('steps_completed', [])),
                    'steps_failed': len(state.get('steps_failed', []))
                })
        return active_workflows
    
    def cleanup_completed_workflows(self, max_age_hours: int = 24):
        """Clean up completed workflows older than specified age"""
        current_time = datetime.utcnow()
        workflows_to_remove = []
        
        for workflow_id, state in self.workflow_state.items():
            if state.get('status') in ['completed', 'failed']:
                end_time = state.get('end_time')
                if end_time and isinstance(end_time, datetime):
                    age_hours = (current_time - end_time).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        workflows_to_remove.append(workflow_id)
        
        for workflow_id in workflows_to_remove:
            del self.workflow_state[workflow_id]
            logger.info(f"Cleaned up completed workflow: {workflow_id}")
    
    def get_insights_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for insights generation"""
        completed_workflows = [
            state for state in self.workflow_state.values() 
            if state.get('status') == 'completed'
        ]
        
        if not completed_workflows:
            return {'no_data': True}
        
        # Calculate average processing time
        processing_times = []
        for state in completed_workflows:
            start_time = state.get('start_time')
            end_time = state.get('end_time')
            if start_time and end_time and isinstance(start_time, datetime) and isinstance(end_time, datetime):
                processing_time = (end_time - start_time).total_seconds()
                processing_times.append(processing_time)
        
        # Calculate success rate
        total_workflows = len(self.workflow_state)
        successful_workflows = len(completed_workflows)
        failed_workflows = len([
            state for state in self.workflow_state.values() 
            if state.get('status') == 'failed'
        ])
        
        return {
            'total_workflows': total_workflows,
            'successful_workflows': successful_workflows,
            'failed_workflows': failed_workflows,
            'success_rate': successful_workflows / total_workflows if total_workflows > 0 else 0,
            'average_processing_time_seconds': statistics.mean(processing_times) if processing_times else 0,
            'cache_hit_rate': len(self.insight_cache) / max(total_workflows, 1),
            'active_workflows': len(self.list_active_workflows())
        }