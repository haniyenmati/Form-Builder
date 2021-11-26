from django.contrib import admin
from .models import *

admin.site.register(Form)
admin.site.register(Question)
admin.site.register(Response)
admin.site.register(LongAnswer)
admin.site.register(ShortAnswer)
admin.site.register(MultipleChoiceAnswer)
admin.site.register(Choices)
admin.site.register(EmailFieldAnswer)
admin.site.register(PhoneNumberFieldAnswer)
admin.site.register(NumberFieldAnswer)
admin.site.register(FileFieldAnswer)
