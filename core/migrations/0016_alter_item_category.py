# Generated by Django 4.2.4 on 2023-10-30 08:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_alter_item_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='category',
            field=models.CharField(choices=[('AC', 'Аксесуари'), ('BC', 'Бейсболки'), ('JK', 'Куртки'), ('CP', 'Кепки'), ('SN', 'Кросівки'), ('PM', 'Піжами'), ('SA', 'Сандалі'), ('SR', 'Сорочки'), ('SW', 'Спортивні костюми'), ('TT', 'Футболки та топи'), ('HS', 'Худі та толстовки'), ('BT', 'Чоботи'), ('PJ', 'Штани та джинси'), ('SH', 'Шорти'), ('SC', 'Шкарпетки')], max_length=2, verbose_name='Категорія'),
        ),
    ]
