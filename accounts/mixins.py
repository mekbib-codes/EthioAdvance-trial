from django.views import View
from django.utils.decorators import method_decorator
from .decorators import (company_required,
                         tutor_required,
                         parent_required,
                         parent_or_tutor_required,
                         company_or_tutor_required,)

@method_decorator(company_required, name='dispatch')
class CompanyRequiredMixin(View):
    pass

@method_decorator(parent_required, name='dispatch')
class ParentRequiredMixin(View):
    pass

@method_decorator(tutor_required, name='dispatch')
class TutorRequiredMixin(View):
    pass

@method_decorator(parent_or_tutor_required, name='dispatch')
class ParentorTutorRequiredMixin(View):
    pass

@method_decorator(company_or_tutor_required, name='dispatch')
class CompanyorTutorRequiredMixin(View):
    pass