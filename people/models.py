from django.db import models

class Agent(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Driver(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Freelancer(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
class Staff(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Staff"