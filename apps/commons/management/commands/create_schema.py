"""
Management command para criar o schema específico da aplicação.
Este comando deve ser executado antes das migrações em produção.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Cria o schema específico da aplicação no PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Nome do schema a ser criado (padrão: valor de DATABASE_SCHEMA)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força a criação mesmo se o schema já existir',
        )

    def handle(self, *args, **options):
        schema_name = options['schema'] or settings.DATABASE_SCHEMA
        
        if schema_name == 'public':
            self.stdout.write(
                self.style.WARNING(
                    'Schema "public" é o padrão do PostgreSQL. '
                    'Não é necessário criar.'
                )
            )
            return

        with connection.cursor() as cursor:
            # Verificar se o schema já existe
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name = %s",
                [schema_name]
            )
            exists = cursor.fetchone()

            if exists and not options['force']:
                self.stdout.write(
                    self.style.WARNING(
                        f'Schema "{schema_name}" já existe. '
                        'Use --force para recriar.'
                    )
                )
                return

            if exists and options['force']:
                self.stdout.write(
                    self.style.WARNING(
                        f'Removendo schema existente "{schema_name}"...'
                    )
                )
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')

            # Criar o schema
            self.stdout.write(f'Criando schema "{schema_name}"...')
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')

            # Definir permissões (usuário atual como owner)
            current_user = connection.get_connection_params().get('user', 'postgres')
            cursor.execute(f'ALTER SCHEMA "{schema_name}" OWNER TO "{current_user}"')

            self.stdout.write(
                self.style.SUCCESS(
                    f'Schema "{schema_name}" criado com sucesso!'
                )
            )
            
            # Informações importantes
            self.stdout.write('')
            self.stdout.write('📌 Próximos passos:')
            self.stdout.write('   1. Execute: python manage.py migrate')
            self.stdout.write('   2. Todas as tabelas serão criadas no schema específico')
            self.stdout.write('')
            self.stdout.write(f'🔍 Para conectar manualmente: SET search_path TO {schema_name};')
