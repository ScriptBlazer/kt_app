from django.db import migrations

def create_bed_types(apps, schema_editor):
    BedType = apps.get_model('hotels', 'BedType')
    BedType.objects.bulk_create([
        BedType(name='Single'),
        BedType(name='Small Double'),
        BedType(name='Double'),
        BedType(name='Queen'),
        BedType(name='King'),
        BedType(name='Superking'),
        BedType(name='Sofa')
    ])

class Migration(migrations.Migration):

    dependencies = [
        ('hotels', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_bed_types),
    ]