"""
Corrige ubicaciones que tienen los placeholders "ciudad", "estado", "pais"
y los reemplaza por "bogota", "cundinamarca", "colombia" (o los valores que indiques).
Así el mapa histórico y los datos en tiempo real muestran el nombre real.

Uso:
  python manage.py fix_placeholder_location
  python manage.py fix_placeholder_location --city bogota --state cundinamarca --country colombia
"""
from django.core.management.base import BaseCommand
from receiver.models import Location, City, State, Country
from receiver.utils import get_coordinates


class Command(BaseCommand):
    help = 'Reemplaza placeholders ciudad/estado/pais por nombres reales (ej. bogota, cundinamarca, colombia)'

    def add_arguments(self, parser):
        parser.add_argument('--city', default='bogota', help='Nombre de ciudad (default: bogota)')
        parser.add_argument('--state', default='cundinamarca', help='Nombre de estado/departamento (default: cundinamarca)')
        parser.add_argument('--country', default='colombia', help='Nombre de país (default: colombia)')

    def handle(self, *args, **options):
        city_name = options['city']
        state_name = options['state']
        country_name = options['country']

        # Ubicaciones que tienen los placeholders literales
        locations = Location.objects.filter(
            city__name='ciudad',
            state__name='estado',
            country__name='pais'
        ).select_related('city', 'state', 'country')

        if not locations.exists():
            self.stdout.write(self.style.WARNING('No hay ubicaciones con "ciudad, estado, pais". Nada que corregir.'))
            return

        city_o, _ = City.objects.get_or_create(name=city_name, defaults={})
        state_o, _ = State.objects.get_or_create(name=state_name, defaults={})
        country_o, _ = Country.objects.get_or_create(name=country_name, defaults={})

        updated = 0
        for loc in locations:
            loc.city = city_o
            loc.state = state_o
            loc.country = country_o
            # Actualizar coordenadas para el mapa
            try:
                lat, lng = get_coordinates(city_name, state_name, country_name)
                if lat and lng:
                    loc.lat = lat
                    loc.lng = lng
            except Exception as e:
                self.stdout.write(self.style.WARNING('Coordenadas no actualizadas: {}'.format(e)))
            loc.save()
            updated += 1
            self.stdout.write('Actualizada Location id={} -> {}, {}, {}'.format(
                loc.pk, city_name, state_name, country_name))

        # Opcional: borrar City/State/Country viejos si ya no los usa nadie
        old_city = City.objects.filter(name='ciudad').first()
        old_state = State.objects.filter(name='estado').first()
        old_country = Country.objects.filter(name='pais').first()
        if old_city and not Location.objects.filter(city=old_city).exists():
            old_city.delete()
            self.stdout.write('Eliminada City "ciudad"')
        if old_state and not Location.objects.filter(state=old_state).exists():
            old_state.delete()
            self.stdout.write('Eliminado State "estado"')
        if old_country and not Location.objects.filter(country=old_country).exists():
            old_country.delete()
            self.stdout.write('Eliminado Country "pais"')

        self.stdout.write(self.style.SUCCESS('Listo. {} ubicación(es) corregida(s). Recarga el mapa histórico.'.format(updated)))
