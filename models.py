from django.db import models

class Milestone(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('active', 'In Progress'),
        ('upcoming', 'Upcoming'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    icon = models.CharField(max_length=50, default="fa-flag")

    class Meta:
        ordering = ['date']

    def __str__(self):
        return self.title