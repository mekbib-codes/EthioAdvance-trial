from django.views.generic import TemplateView

class AboutView(TemplateView):
    template_name = "footer_pages/about.html"

class FAQView(TemplateView):
    template_name = "footer_pages/faq.html"

class PrivacyPolicyView(TemplateView):
    template_name = "footer_pages/privacy_policy.html"

class TermsOfServiceView(TemplateView):
    template_name = "footer_pages/terms_of_service.html"