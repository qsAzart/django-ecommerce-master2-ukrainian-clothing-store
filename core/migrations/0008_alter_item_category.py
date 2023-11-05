# Generated by Django 4.2.4 on 2023-10-25 18:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_item_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='category',
            field=models.CharField(choices=[('TT', 'Футболки та топи'), ('SW', 'Спортивні костюми'), ('S', 'Сорочки'), ('H', 'Худі та толстовки'), ('SH', 'Шорти'), ('J', 'Куртки'), ('SN', 'Кросівки'), ('SA', 'Сандалі'), ('BT', 'Чоботи'), ('SC', 'Шкарпетки')], max_length=2, verbose_name='Категорія'),
        ),
    ]
