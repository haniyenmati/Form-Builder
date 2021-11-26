from django.db import models


class AbstractBaseQuestion(models.Model):
    question_body = models.CharField(max_length=256)
    related_image = models.ImageField(null=True, blank=True, upload_to='media/question_related_images')

    def __str__(self):
        return self.question_body

    class Meta:
        abstract = True
