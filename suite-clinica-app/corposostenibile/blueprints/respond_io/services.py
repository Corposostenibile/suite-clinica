"""
Servizi per calcolo metriche e analisi funnel - versione semplificata
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_, extract, case
from collections import defaultdict
import calendar
from corposostenibile.extensions import db
from corposostenibile.models import (
    RespondIOLifecycleChange,
    RespondIODailyMetrics,
    RESPOND_IO_CHANNELS
)


class FunnelAnalyticsService:
    """Servizio per analisi funnel basato su metriche aggregate"""
    
    # Definizione del funnel principale
    FUNNEL_STAGES = [
        ('Nuova Lead', 'Contrassegnato'),
        ('Contrassegnato', 'In Target'),
        ('In Target', 'Link Da Inviare'),
        ('Link Da Inviare', 'Link Inviato'),
        ('Link Inviato', 'Prenotato'),
    ]
    
    @classmethod
    def calculate_funnel_metrics(cls, 
                                 start_date: date,
                                 end_date: date,
                                 channel_source: Optional[str] = None) -> Dict:
        """
        Calcola le metriche del funnel aggregando i dati giornalieri
        """
        metrics = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'channels': {},
            'totals': {
                'new_leads': 0,
                'conversions': {},
                'exits': {}
            }
        }
        
        # Query per aggregare metriche nel periodo
        # NUOVO: Usiamo i campi totali per gli stati, non le transizioni
        query = db.session.query(
            RespondIODailyMetrics.channel_name,
            func.max(RespondIODailyMetrics.channel_source).label('channel_source'),  # Usa MAX per ottenere un valore
            func.sum(RespondIODailyMetrics.new_leads).label('total_new_leads'),
            func.sum(RespondIODailyMetrics.total_contrassegnato).label('total_contrassegnato'),
            func.sum(RespondIODailyMetrics.total_in_target).label('total_in_target'),
            func.sum(RespondIODailyMetrics.total_link_da_inviare).label('total_link_da_inviare'),
            func.sum(RespondIODailyMetrics.total_link_inviato).label('total_link_inviato'),
            func.sum(RespondIODailyMetrics.total_prenotato).label('total_prenotato'),
            # Manteniamo anche le transizioni per analisi del flusso
            func.sum(RespondIODailyMetrics.lead_to_contrassegnato).label('flow_lead_to_contrassegnato'),
            func.sum(RespondIODailyMetrics.contrassegnato_to_target).label('flow_contrassegnato_to_target'),
            func.sum(RespondIODailyMetrics.target_to_link_da_inviare).label('flow_target_to_link_da_inviare'),
            func.sum(RespondIODailyMetrics.link_da_inviare_to_link_inviato).label('flow_link_da_inviare_to_link_inviato'),
            func.sum(RespondIODailyMetrics.link_to_prenotato).label('flow_link_to_prenotato'),
            func.sum(RespondIODailyMetrics.to_under).label('total_to_under'),
            func.sum(RespondIODailyMetrics.to_non_target).label('total_to_non_target'),
            func.sum(RespondIODailyMetrics.to_prenotato_non_target).label('total_to_prenotato_non_target')
        ).filter(
            RespondIODailyMetrics.date.between(start_date, end_date)
        ).group_by(
            RespondIODailyMetrics.channel_name  # Raggruppa solo per channel_name
        )
        
        # Filtra per canale se specificato
        if channel_source:
            query = query.filter(RespondIODailyMetrics.channel_source == channel_source)
        
        results = query.all()
        
        # Processa risultati
        for row in results:
            channel_metrics = {
                'channel': row.channel_name or 'Unknown',
                'new_leads': row.total_new_leads or 0,  # Retrocompatibilità
                # TOTALI per stato (quante volte i contatti sono stati messi in quello stato)
                'totals': {
                    'new_leads': row.total_new_leads or 0,
                    'contrassegnato': row.total_contrassegnato or 0,
                    'in_target': row.total_in_target or 0,
                    'link_da_inviare': row.total_link_da_inviare or 0,
                    'link_inviato': row.total_link_inviato or 0,
                    'prenotato': row.total_prenotato or 0,
                },
                # Flusso delle transizioni (per analisi del percorso)
                'flow': {
                    'lead_to_contrassegnato': row.flow_lead_to_contrassegnato or 0,
                    'contrassegnato_to_target': row.flow_contrassegnato_to_target or 0,
                    'target_to_link_da_inviare': row.flow_target_to_link_da_inviare or 0,
                    'link_da_inviare_to_link_inviato': row.flow_link_da_inviare_to_link_inviato or 0,
                    'link_to_prenotato': row.flow_link_to_prenotato or 0,
                },
                # Retrocompatibilità: mantieni anche 'conversions'
                'conversions': {
                    'nuova_lead_to_contrassegnato': row.flow_lead_to_contrassegnato or 0,
                    'contrassegnato_to_in_target': row.flow_contrassegnato_to_target or 0,
                    'in_target_to_link_da_inviare': row.flow_target_to_link_da_inviare or 0,
                    'link_da_inviare_to_link_inviato': row.flow_link_da_inviare_to_link_inviato or 0,
                    'link_inviato_to_prenotato': row.flow_link_to_prenotato or 0,
                },
                'exits': {
                    'to_under': row.total_to_under or 0,
                    'to_non_target': row.total_to_non_target or 0,
                    'to_prenotato_non_target': row.total_to_prenotato_non_target or 0
                },
                'conversion_rates': {}
            }
            
            # Calcola percentuali di conversione
            cls._calculate_conversion_rates_for_channel(channel_metrics)
            
            # Aggiungi ai risultati
            channel_name = row.channel_name or 'Unknown'
            metrics['channels'][channel_name] = channel_metrics
            
            # Aggiungi ai totali
            metrics['totals']['new_leads'] += channel_metrics['totals']['new_leads']
            
            # Aggiungi totali per stato
            if 'states' not in metrics['totals']:
                metrics['totals']['states'] = {}
            for key, value in channel_metrics['totals'].items():
                if key not in metrics['totals']['states']:
                    metrics['totals']['states'][key] = 0
                metrics['totals']['states'][key] += value
            
            # Aggiungi totali del flusso
            if 'flow' not in metrics['totals']:
                metrics['totals']['flow'] = {}
            for key, value in channel_metrics['flow'].items():
                if key not in metrics['totals']['flow']:
                    metrics['totals']['flow'][key] = 0
                metrics['totals']['flow'][key] += value
            
            # Aggiungi totali exits
            for key, value in channel_metrics['exits'].items():
                if key not in metrics['totals']['exits']:
                    metrics['totals']['exits'][key] = 0
                metrics['totals']['exits'][key] += value
        
        return metrics
    
    @classmethod
    def _calculate_conversion_rates_for_channel(cls, channel_metrics: Dict) -> None:
        """Calcola le percentuali di conversione per un canale"""
        
        # Supporta sia la vecchia struttura 'conversions' che la nuova 'flow'
        if 'flow' in channel_metrics:
            conversions = channel_metrics['flow']
        elif 'conversions' in channel_metrics:
            conversions = channel_metrics['conversions']
        else:
            # Se non ci sono dati di flusso, usa i totali per calcolare approssimativamente
            channel_metrics['conversion_rates'] = {}
            return
        
        rates = {}
        
        # Usa i totali per calcolare le percentuali basate sugli stati effettivi
        if 'totals' in channel_metrics:
            totals = channel_metrics['totals']
            
            # Percentuali basate sui totali degli stati
            if totals.get('new_leads', 0) > 0:
                base = totals['new_leads']
                
                if totals.get('contrassegnato', 0) > 0:
                    rates['lead_to_contrassegnato'] = round((totals['contrassegnato'] / base) * 100, 1)
                
                if totals.get('in_target', 0) > 0:
                    rates['lead_to_in_target'] = round((totals['in_target'] / base) * 100, 1)
                
                if totals.get('link_inviato', 0) > 0:
                    rates['lead_to_link_inviato'] = round((totals['link_inviato'] / base) * 100, 1)
                
                if totals.get('prenotato', 0) > 0:
                    rates['lead_to_prenotato'] = round((totals['prenotato'] / base) * 100, 1)
        
        else:
            # Fallback: usa il vecchio metodo basato sulle transizioni
            # Prima cerca new_leads in totals, poi come fallback nel root
            base_count = 0
            if 'totals' in channel_metrics and 'new_leads' in channel_metrics['totals']:
                base_count = channel_metrics['totals']['new_leads']
            elif 'new_leads' in channel_metrics:
                base_count = channel_metrics['new_leads']
            
            if base_count > 0:
                # Lead → Contrassegnato
                key = 'lead_to_contrassegnato'
                if key in conversions and conversions[key] > 0:
                    rates[key] = round((conversions[key] / base_count) * 100, 1)
                    base_count = conversions[key]
                
                # Altri step del funnel...
                # Semplificato per brevità
        
        channel_metrics['conversion_rates'] = rates
    
    @classmethod
    def get_daily_breakdown(cls,
                            start_date: date,
                            end_date: date,
                            channel_source: Optional[str] = None) -> List[Dict]:
        """
        Ottiene breakdown giornaliero delle metriche.
        NUOVO: Include sia i totali per stato che le transizioni.
        """
        query = db.session.query(RespondIODailyMetrics)\
            .filter(RespondIODailyMetrics.date.between(start_date, end_date))
        
        if channel_source:
            query = query.filter(RespondIODailyMetrics.channel_source == channel_source)
        
        daily_data = query.order_by(RespondIODailyMetrics.date).all()
        
        result = []
        for day_record in daily_data:
            result.append({
                'date': day_record.date.isoformat(),
                'channel': day_record.channel_name,
                'new_leads': day_record.new_leads or 0,
                # NUOVI CAMPI: Totali per stato
                'totals': {
                    'contrassegnato': day_record.total_contrassegnato or 0,
                    'in_target': day_record.total_in_target or 0,
                    'link_da_inviare': day_record.total_link_da_inviare or 0,
                    'link_inviato': day_record.total_link_inviato or 0,
                    'prenotato': day_record.total_prenotato or 0,
                },
                # Manteniamo le conversioni per retrocompatibilità
                'conversions': {
                    'lead_to_contrassegnato': day_record.lead_to_contrassegnato or 0,
                    'contrassegnato_to_target': day_record.contrassegnato_to_target or 0,
                    'target_to_link_da_inviare': day_record.target_to_link_da_inviare or 0,
                    'link_da_inviare_to_link_inviato': day_record.link_da_inviare_to_link_inviato or 0,
                    'link_to_prenotato': day_record.link_to_prenotato or 0,
                }
            })
        
        return result
    
    @classmethod
    def recalculate_daily_metrics(cls, target_date: date, channel: Optional[str] = None):
        """
        Ricalcola le metriche giornaliere basandosi sui lifecycle changes.
        NUOVO: Contiamo sia i totali per stato che le transizioni.
        """
        # Usa i nomi dei canali invece dei numeri di telefono
        channels = [channel] if channel else RESPOND_IO_CHANNELS.values()
        
        # Converti date in datetime per le query
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        for channel_name in channels:
            # Query 1: Conta TUTTI i lifecycle in cui sono stati messi i contatti nel giorno
            # Filtra per channel_name invece di channel_source
            lifecycle_counts = db.session.query(
                RespondIOLifecycleChange.to_lifecycle,
                func.count(RespondIOLifecycleChange.id).label('count')
            ).filter(
                RespondIOLifecycleChange.channel_name == channel_name,
                RespondIOLifecycleChange.changed_at.between(start_datetime, end_datetime)
            ).group_by(
                RespondIOLifecycleChange.to_lifecycle
            ).all()
            
            # Query 2: Conta le transizioni specifiche (per analisi del flusso)
            transitions = db.session.query(
                RespondIOLifecycleChange.from_lifecycle,
                RespondIOLifecycleChange.to_lifecycle,
                func.count(RespondIOLifecycleChange.id).label('count')
            ).filter(
                RespondIOLifecycleChange.channel_name == channel_name,
                RespondIOLifecycleChange.changed_at.between(start_datetime, end_datetime)
            ).group_by(
                RespondIOLifecycleChange.from_lifecycle,
                RespondIOLifecycleChange.to_lifecycle
            ).all()
            
            # Trova o crea record giornaliero
            # Usa channel_name come chiave univoca
            daily_record = RespondIODailyMetrics.query.filter_by(
                date=target_date,
                channel_name=channel_name
            ).first()
            
            if not daily_record:
                # Trova il channel_source (numero) dal mapping inverso, o usa 'whatsapp_business' di default
                channel_source = 'whatsapp_business'
                for num, name in RESPOND_IO_CHANNELS.items():
                    if name == channel_name:
                        channel_source = num
                        break
                
                daily_record = RespondIODailyMetrics(
                    date=target_date,
                    channel_source=channel_source,
                    channel_name=channel_name
                )
                db.session.add(daily_record)
            
            # Reset TUTTI i contatori
            daily_record.new_leads = 0
            daily_record.total_contrassegnato = 0
            daily_record.total_in_target = 0
            daily_record.total_link_da_inviare = 0
            daily_record.total_link_inviato = 0
            daily_record.total_prenotato = 0
            daily_record.lead_to_contrassegnato = 0
            daily_record.contrassegnato_to_target = 0
            daily_record.target_to_link_da_inviare = 0
            daily_record.link_da_inviare_to_link_inviato = 0
            daily_record.target_to_link = 0
            daily_record.link_to_prenotato = 0
            daily_record.to_under = 0
            daily_record.to_non_target = 0
            daily_record.to_prenotato_non_target = 0
            
            # Aggiorna contatori TOTALI per ogni stato
            for to_lc, count in lifecycle_counts:
                if to_lc == 'Nuova Lead':
                    daily_record.new_leads += count
                elif to_lc == 'Contrassegnato':
                    daily_record.total_contrassegnato += count
                elif to_lc == 'In Target':
                    daily_record.total_in_target += count
                elif to_lc == 'Link Da Inviare':
                    daily_record.total_link_da_inviare += count
                elif to_lc == 'Link Inviato':
                    daily_record.total_link_inviato += count
                elif to_lc == 'Prenotato':
                    daily_record.total_prenotato += count
                elif to_lc == 'Under':
                    daily_record.to_under += count
                elif to_lc == 'Non in Target':
                    daily_record.to_non_target += count
                elif to_lc == 'Prenotato Non In Target':
                    daily_record.to_prenotato_non_target += count
            
            # Aggiorna contatori delle TRANSIZIONI (per analisi del flusso)
            for from_lc, to_lc, count in transitions:
                if from_lc == 'Nuova Lead' and to_lc == 'Contrassegnato':
                    daily_record.lead_to_contrassegnato += count
                elif from_lc == 'Contrassegnato' and to_lc == 'In Target':
                    daily_record.contrassegnato_to_target += count
                elif from_lc == 'In Target' and to_lc == 'Link Da Inviare':
                    daily_record.target_to_link_da_inviare += count
                elif from_lc == 'Link Da Inviare' and to_lc == 'Link Inviato':
                    daily_record.link_da_inviare_to_link_inviato += count
                elif from_lc == 'In Target' and to_lc == 'Link Inviato':
                    # Compatibilità: transizione diretta senza passare da Link Da Inviare
                    daily_record.target_to_link += count
                elif from_lc == 'Link Inviato' and to_lc == 'Prenotato':
                    daily_record.link_to_prenotato += count
            
            daily_record.updated_at = datetime.utcnow()
        
        db.session.commit()
    
    @classmethod
    def get_channel_ranking_by_month(cls, year: int, month: int) -> List[Dict]:
        """
        Ranking mensile dei canali per conversion rate finale (lead → prenotato)
        """
        # Date del mese
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Query aggregata per il mese
        results = db.session.query(
            RespondIODailyMetrics.channel_name,
            func.sum(RespondIODailyMetrics.new_leads).label('total_leads'),
            func.sum(RespondIODailyMetrics.link_to_prenotato).label('total_prenotato')
        ).filter(
            RespondIODailyMetrics.date.between(start_date, end_date)
        ).group_by(
            RespondIODailyMetrics.channel_name
        ).all()
        
        # Calcola ranking
        ranking = []
        for row in results:
            if row.total_leads and row.total_leads > 0:
                conversion_rate = (row.total_prenotato or 0) / row.total_leads * 100
            else:
                conversion_rate = 0
            
            ranking.append({
                'channel': row.channel_name,
                'total_leads': row.total_leads or 0,
                'total_prenotato': row.total_prenotato or 0,
                'conversion_rate': round(conversion_rate, 2),
                'month': calendar.month_name[month],
                'year': year
            })
        
        # Ordina per conversion rate
        ranking.sort(key=lambda x: x['conversion_rate'], reverse=True)
        
        # Aggiungi posizione
        for i, item in enumerate(ranking, 1):
            item['rank'] = i
        
        return ranking
    
    @classmethod
    def get_hourly_heatmap(cls, start_date: date, end_date: date) -> Dict:
        """
        Heatmap oraria: quando arrivano più lead per canale (ore x giorni settimana)
        """
        # Query lifecycle changes per ora e giorno settimana
        results = db.session.query(
            RespondIOLifecycleChange.channel_name,
            extract('hour', RespondIOLifecycleChange.changed_at).label('hour'),
            extract('dow', RespondIOLifecycleChange.changed_at).label('weekday'),
            func.count(RespondIOLifecycleChange.id).label('count')
        ).filter(
            RespondIOLifecycleChange.from_lifecycle.is_(None),
            RespondIOLifecycleChange.to_lifecycle == 'Nuova Lead',
            RespondIOLifecycleChange.changed_at >= datetime.combine(start_date, datetime.min.time()),
            RespondIOLifecycleChange.changed_at <= datetime.combine(end_date, datetime.max.time())
        ).group_by(
            RespondIOLifecycleChange.channel_name,
            'hour',
            'weekday'
        ).all()
        
        # Struttura dati per heatmap
        heatmap_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        
        weekdays = ['Domenica', 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato']
        
        for row in results:
            channel = row.channel_name or 'Unknown'
            hour = int(row.hour)
            weekday = weekdays[int(row.weekday)]
            heatmap_data[channel][weekday][hour] = row.count
        
        # Converti in formato più usabile
        result = {}
        for channel, weekday_data in heatmap_data.items():
            result[channel] = {
                'data': [],
                'max_value': 0
            }
            for weekday in weekdays:
                for hour in range(24):
                    value = weekday_data[weekday][hour]
                    result[channel]['data'].append({
                        'weekday': weekday,
                        'hour': hour,
                        'value': value
                    })
                    result[channel]['max_value'] = max(result[channel]['max_value'], value)
        
        return result
    
    @classmethod
    def get_peak_performance_times(cls, start_date: date, end_date: date) -> Dict:
        """
        Identifica quando ogni canale performa meglio per conversioni e nuovi lead
        """
        result = {
            'conversions': {},  # Link Inviato → Prenotato
            'new_leads': {}     # Nuovi Lead
        }
        
        # 1. Query per CONVERSIONI (Link Inviato → Prenotato)
        conversions_results = db.session.query(
            RespondIOLifecycleChange.channel_name,
            extract('hour', RespondIOLifecycleChange.changed_at).label('hour'),
            func.count(RespondIOLifecycleChange.id).label('count')
        ).filter(
            RespondIOLifecycleChange.from_lifecycle == 'Link Inviato',
            RespondIOLifecycleChange.to_lifecycle == 'Prenotato',
            RespondIOLifecycleChange.changed_at >= datetime.combine(start_date, datetime.min.time()),
            RespondIOLifecycleChange.changed_at <= datetime.combine(end_date, datetime.max.time())
        ).group_by(
            RespondIOLifecycleChange.channel_name,
            'hour'
        ).all()
        
        # Processa conversioni
        channel_hours_conv = defaultdict(list)
        for row in conversions_results:
            channel = row.channel_name or 'Unknown'
            channel_hours_conv[channel].append({
                'hour': int(row.hour),
                'count': row.count
            })
        
        for channel, hours in channel_hours_conv.items():
            hours.sort(key=lambda x: x['count'], reverse=True)
            top_hours = hours[:3]
            
            result['conversions'][channel] = {
                'best_hour': top_hours[0]['hour'] if top_hours else None,
                'best_hour_count': top_hours[0]['count'] if top_hours else 0,
                'top_3_hours': [h['hour'] for h in top_hours],
                'hourly_distribution': hours
            }
        
        # 2. Query per NUOVI LEAD (from_lifecycle is None, to_lifecycle = 'Nuova Lead')
        new_leads_results = db.session.query(
            RespondIOLifecycleChange.channel_name,
            extract('hour', RespondIOLifecycleChange.changed_at).label('hour'),
            func.count(RespondIOLifecycleChange.id).label('count')
        ).filter(
            RespondIOLifecycleChange.from_lifecycle.is_(None),
            RespondIOLifecycleChange.to_lifecycle == 'Nuova Lead',
            RespondIOLifecycleChange.changed_at >= datetime.combine(start_date, datetime.min.time()),
            RespondIOLifecycleChange.changed_at <= datetime.combine(end_date, datetime.max.time())
        ).group_by(
            RespondIOLifecycleChange.channel_name,
            'hour'
        ).all()
        
        # Processa nuovi lead
        channel_hours_leads = defaultdict(list)
        for row in new_leads_results:
            channel = row.channel_name or 'Unknown'
            channel_hours_leads[channel].append({
                'hour': int(row.hour),
                'count': row.count
            })
        
        for channel, hours in channel_hours_leads.items():
            hours.sort(key=lambda x: x['count'], reverse=True)
            top_hours = hours[:3]
            
            result['new_leads'][channel] = {
                'best_hour': top_hours[0]['hour'] if top_hours else None,
                'best_hour_count': top_hours[0]['count'] if top_hours else 0,
                'top_3_hours': [h['hour'] for h in top_hours],
                'hourly_distribution': hours
            }
        
        return result
    
    @classmethod
    def get_benchmark_analysis(cls, start_date: date, end_date: date) -> Dict:
        """
        Benchmark tra canali con media aziendale
        """
        metrics = cls.calculate_funnel_metrics(start_date, end_date)
        
        # Calcola medie aziendali
        total_channels = len(metrics['channels'])
        if total_channels == 0:
            return {'channels': {}, 'company_average': {}}
        
        company_average = {
            'new_leads': metrics['totals']['new_leads'] / total_channels,
            'conversion_rate': 0
        }
        
        # Conversion rate medio
        total_leads = metrics['totals']['new_leads']
        total_prenotato = metrics['totals']['conversions'].get('link_inviato_to_prenotato', 0)
        if total_leads > 0:
            company_average['conversion_rate'] = (total_prenotato / total_leads) * 100
        
        # Confronta ogni canale con la media
        benchmark = {
            'channels': {},
            'company_average': company_average
        }
        
        for channel_name, channel_data in metrics['channels'].items():
            channel_conversion_rate = 0
            if channel_data['new_leads'] > 0:
                channel_conversion_rate = (channel_data['conversions'].get('link_inviato_to_prenotato', 0) / 
                                          channel_data['new_leads']) * 100
            
            benchmark['channels'][channel_name] = {
                'new_leads': channel_data['new_leads'],
                'conversion_rate': round(channel_conversion_rate, 2),
                'vs_average_leads': channel_data['new_leads'] - company_average['new_leads'],
                'vs_average_conversion': round(channel_conversion_rate - company_average['conversion_rate'], 2),
                'performance_index': round((channel_conversion_rate / company_average['conversion_rate'] * 100) 
                                         if company_average['conversion_rate'] > 0 else 0, 1)
            }
        
        return benchmark
    
    @classmethod
    def get_period_comparison(cls, current_start: date, current_end: date) -> Dict:
        """
        Delta vs periodo precedente (settimana/mese scorso)
        """
        # Calcola periodo precedente
        period_length = (current_end - current_start).days + 1
        prev_end = current_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_length - 1)
        
        # Metriche periodo corrente
        current_metrics = cls.calculate_funnel_metrics(current_start, current_end)
        
        # Metriche periodo precedente  
        prev_metrics = cls.calculate_funnel_metrics(prev_start, prev_end)
        
        # Calcola delta
        comparison = {
            'current_period': {
                'start': current_start.isoformat(),
                'end': current_end.isoformat()
            },
            'previous_period': {
                'start': prev_start.isoformat(),
                'end': prev_end.isoformat()
            },
            'totals': {},
            'channels': {}
        }
        
        # Delta totali
        comparison['totals'] = {
            'new_leads': {
                'current': current_metrics['totals']['new_leads'],
                'previous': prev_metrics['totals']['new_leads'],
                'delta': current_metrics['totals']['new_leads'] - prev_metrics['totals']['new_leads'],
                'delta_percent': cls._calculate_percent_change(
                    prev_metrics['totals']['new_leads'],
                    current_metrics['totals']['new_leads']
                )
            }
        }
        
        # Delta per conversioni
        for key in ['nuova_lead_to_contrassegnato', 'contrassegnato_to_in_target', 
                   'in_target_to_link_da_inviare', 'link_da_inviare_to_link_inviato',
                   'link_inviato_to_prenotato']:
            current_val = current_metrics['totals']['conversions'].get(key, 0)
            prev_val = prev_metrics['totals']['conversions'].get(key, 0)
            comparison['totals'][key] = {
                'current': current_val,
                'previous': prev_val,
                'delta': current_val - prev_val,
                'delta_percent': cls._calculate_percent_change(prev_val, current_val)
            }
        
        # Delta per canale
        all_channels = set(list(current_metrics['channels'].keys()) + 
                          list(prev_metrics['channels'].keys()))
        
        for channel in all_channels:
            current_ch = current_metrics['channels'].get(channel, {})
            prev_ch = prev_metrics['channels'].get(channel, {})
            
            comparison['channels'][channel] = {
                'new_leads': {
                    'current': current_ch.get('new_leads', 0),
                    'previous': prev_ch.get('new_leads', 0),
                    'delta': current_ch.get('new_leads', 0) - prev_ch.get('new_leads', 0),
                    'delta_percent': cls._calculate_percent_change(
                        prev_ch.get('new_leads', 0),
                        current_ch.get('new_leads', 0)
                    )
                }
            }
        
        return comparison
    
    @classmethod
    def get_bottleneck_analysis(cls, start_date: date, end_date: date) -> Dict:
        """
        Identifica dove si perde più gente nel funnel
        """
        metrics = cls.calculate_funnel_metrics(start_date, end_date)
        
        bottlenecks = {
            'worst_step': None,
            'worst_step_loss_rate': 0,
            'by_channel': {},
            'steps': []
        }
        
        # Analisi per step del funnel
        funnel_steps = [
            ('Nuova Lead', 'nuova_lead_to_contrassegnato', 'Contrassegnato'),
            ('Contrassegnato', 'contrassegnato_to_in_target', 'In Target'),
            ('In Target', 'in_target_to_link_da_inviare', 'Link Da Inviare'),
            ('Link Da Inviare', 'link_da_inviare_to_link_inviato', 'Link Inviato'),
            ('Link Inviato', 'link_inviato_to_prenotato', 'Prenotato')
        ]
        
        for i, (from_stage, conversion_key, to_stage) in enumerate(funnel_steps):
            conversions = metrics['totals']['conversions'].get(conversion_key, 0)
            
            # Calcola base per questo step
            if i == 0:
                base = metrics['totals']['new_leads']
            else:
                # Base è il numero di conversioni dello step precedente
                prev_key = funnel_steps[i-1][1]
                base = metrics['totals']['conversions'].get(prev_key, 0)
            
            if base > 0:
                conversion_rate = (conversions / base) * 100
                loss_rate = 100 - conversion_rate
            else:
                conversion_rate = 0
                loss_rate = 0
            
            step_analysis = {
                'from': from_stage,
                'to': to_stage,
                'base_count': base,
                'converted': conversions,
                'lost': base - conversions if base > 0 else 0,
                'conversion_rate': round(conversion_rate, 2),
                'loss_rate': round(loss_rate, 2)
            }
            
            bottlenecks['steps'].append(step_analysis)
            
            # Identifica il peggior bottleneck
            if loss_rate > bottlenecks['worst_step_loss_rate'] and base > 0:
                bottlenecks['worst_step'] = f"{from_stage} → {to_stage}"
                bottlenecks['worst_step_loss_rate'] = round(loss_rate, 2)
        
        # Analisi per canale
        for channel_name, channel_data in metrics['channels'].items():
            channel_bottlenecks = []
            
            for i, (from_stage, conversion_key, to_stage) in enumerate(funnel_steps):
                conversions = channel_data['conversions'].get(conversion_key, 0)
                
                if i == 0:
                    base = channel_data['new_leads']
                else:
                    prev_key = funnel_steps[i-1][1]
                    base = channel_data['conversions'].get(prev_key, 0)
                
                if base > 0:
                    loss_rate = 100 - (conversions / base * 100)
                else:
                    loss_rate = 0
                
                if loss_rate > 50:  # Bottleneck significativo se perdi più del 50%
                    channel_bottlenecks.append({
                        'step': f"{from_stage} → {to_stage}",
                        'loss_rate': round(loss_rate, 2)
                    })
            
            if channel_bottlenecks:
                bottlenecks['by_channel'][channel_name] = channel_bottlenecks
        
        return bottlenecks
    
    @staticmethod
    def _calculate_percent_change(old_value: float, new_value: float) -> float:
        """Calcola variazione percentuale"""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        return round(((new_value - old_value) / old_value) * 100, 1)