"""
Django command to wait for the database to be available
"""
import time

from psycopg2 import OperationalError as Pyscopg2Error

from django.core.management.base import BaseCommand
from django.db.utils import OperationalError

class Command(BaseCommand):
    """ 
        Django command to wait for database 
    """
    def handle(self, *args, **kwargs):
        """ Entrypoint for command. """
        self.stdout.write("Waiting for databases...")
        db_up = False
        while db_up is False:
            try:
                self.check(databases=['default'])
                db_up = True
            except (Pyscopg2Error, OperationalError):
                self.stdout.write("Database unavailable, wait for a second...")
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS("Database Available"))
