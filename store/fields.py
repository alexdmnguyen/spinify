from django.db import models

class CharFieldPrimaryKey(models.CharField):
    def get_prep_value(self, value):
        return str(value)
