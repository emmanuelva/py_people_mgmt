import re
from datetime import datetime

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from people.models import Person, Tag

TAG_COLUMN = ' STATUS'

GENDER_MAP = {
    'HOMBRE': Person.Gender.MALE,
    'MUJER': Person.Gender.FEMALE,
}

MARITAL_STATUS_MAP = {
    'CASADO': Person.MaritalStatus.MARRIED,
    'SOLTERO': Person.MaritalStatus.SINGLE,
    'SOLTERA': Person.MaritalStatus.SINGLE,
    'JOVEN': Person.MaritalStatus.SINGLE,
    'VIUDO': Person.MaritalStatus.WIDOWED,
    'DIVORCIADO': Person.MaritalStatus.DIVORCED,
    'SEPARADO': Person.MaritalStatus.SEPARATED,
}

MEMBER_STATUS_MAP = {
    'SI': Person.Status.ACTIVE,
    'NO': Person.Status.INACTIVE,
}


def clean_phone(value):
    if pd.isna(value):
        return ''
    return re.sub(r'[^0-9]', '', str(value))


def parse_dob(value):
    if pd.isna(value):
        return None
    return datetime.strptime(str(value).strip(), '%d/%m/%Y').date()


def map_choice(value, mapping, default):
    if pd.isna(value):
        return default
    return mapping.get(str(value).strip().upper(), default)


class Command(BaseCommand):
    help = 'Import people from the membresia CSV export (see ai_context/02_data_migration_from_csv.md) into the Person catalog.'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_path',
            nargs='?',
            default='import/membresia.csv',
            help='Path to the membresia CSV file (default: import/membresia.csv).',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except FileNotFoundError as exc:
            raise CommandError(f'CSV file not found: {csv_path}') from exc

        created_count = 0
        updated_count = 0
        error_count = 0

        for _, row in df.iterrows():
            name = str(row['NOMBRE']).strip() if not pd.isna(row['NOMBRE']) else ''
            if not name:
                self.stderr.write(self.style.WARNING(f"Row {row['No']}: missing NOMBRE, skipping"))
                error_count += 1
                continue

            try:
                dob = parse_dob(row['FECHA NACIMIENTO'])
            except ValueError:
                self.stderr.write(self.style.WARNING(
                    f"Row {row['No']}: unparseable FECHA NACIMIENTO {row['FECHA NACIMIENTO']!r}, leaving dob blank"
                ))
                dob = None

            defaults = {
                'name': name,
                'phone': clean_phone(row['TELEFONO']),
                'dob': dob,
                'gender': map_choice(row['SEXO'], GENDER_MAP, Person.Gender.MALE),
                'marital_status': map_choice(row['ESTADO CIVIL'], MARITAL_STATUS_MAP, Person.MaritalStatus.SINGLE),
                'status': map_choice(row['MIEMBRO ACTIVO'], MEMBER_STATUS_MAP, Person.Status.INACTIVE),
            }

            try:
                with transaction.atomic():
                    person, was_created = Person.objects.update_or_create(
                        external_id=int(row['No']),
                        defaults=defaults,
                    )

                    tag_value = row[TAG_COLUMN]
                    if not pd.isna(tag_value):
                        tag_name = str(tag_value).strip()
                        if tag_name:
                            tag, _ = Tag.objects.get_or_create(name=tag_name)
                            person.tags.add(tag)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"Row {row['No']}: failed to import ({exc})"))
                error_count += 1
                continue

            if was_created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Import finished: {created_count} created, {updated_count} updated, {error_count} errors.'
        ))
