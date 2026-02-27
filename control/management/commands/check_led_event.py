"""
Comando para verificar si hay datos de temperatura y si se dispararía el evento LED.
Uso: python manage.py check_led_event
"""
from django.core.management.base import BaseCommand
from django.db.models import Avg
from datetime import timedelta, datetime
from receiver.models import Data

from control.monitor import LED_EVENT_TEMP_THRESHOLD, evaluate_led_event


class Command(BaseCommand):
    help = 'Verifica datos de temperatura y opcionalmente envía LED_ON (--send)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send',
            action='store_true',
            help='Ejecutar evaluate_led_event y enviar LED_ON si aplica',
        )

    def handle(self, *args, **options):
        data = Data.objects.filter(
            base_time__gte=datetime.now() - timedelta(hours=1),
            measurement__name='temperatura'
        )
        aggregation = data.values(
            'station__user__username',
            'station__location__city__name',
            'station__location__state__name',
            'station__location__country__name'
        ).annotate(temperatura_promedio=Avg('avg_value'))

        if not aggregation:
            self.stdout.write(
                self.style.WARNING(
                    'No hay datos de temperatura en la última hora. '
                    '¿El receptor (start_mqtt) está corriendo y el dispositivo publicando?'
                )
            )
            return

        self.stdout.write('Umbral para LED: {} °C\n'.format(LED_EVENT_TEMP_THRESHOLD))
        for item in aggregation:
            temp = item.get('temperatura_promedio')
            topic = '{}/{}/{}/{}/in'.format(
                item['station__location__country__name'],
                item['station__location__state__name'],
                item['station__location__city__name'],
                item['station__user__username'],
            )
            dispara = temp is not None and temp > LED_EVENT_TEMP_THRESHOLD
            self.stdout.write(
                '  {} | temp_prom = {:.1f} °C | ¿Dispara LED? {}'.format(
                    topic, temp or 0, 'Sí' if dispara else 'No'
                )
            )

        if options['send']:
            self.stdout.write('')
            from control import monitor
            monitor.setup_mqtt()
            evaluate_led_event()
            self.stdout.write(self.style.SUCCESS('Listo. Si había temp > umbral, se envió LED_ON. Revisa el NodeMCU (Serial/OLED/LED).'))
