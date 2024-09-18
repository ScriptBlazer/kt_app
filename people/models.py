from django.db import models

class Agent(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Driver(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name