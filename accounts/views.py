from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView

from billing.models import Plan
from .forms import SignInForm, SignUpForm


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'accounts/sign_up.html'
    success_url = reverse_lazy('studio:dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('studio:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        free_plan = Plan.objects.filter(slug='free').first()
        if free_plan:
            self.object.plan = free_plan
            self.object.credits_balance = free_plan.monthly_credits
            self.object.save(update_fields=['plan', 'credits_balance'])
        login(self.request, self.object)
        messages.success(self.request, 'Welcome to 8K Studio! You have %s free credits to start.' % self.object.credits_balance)
        return response


class SignInView(LoginView):
    form_class = SignInForm
    template_name = 'accounts/sign_in.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return str(reverse_lazy('studio:dashboard'))


class SignOutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, 'You have been signed out.')
        return redirect('corepages:home')

    def post(self, request):
        return self.get(request)


@login_required
def profile(request):
    if request.method == 'POST':
        request.user.username = request.POST.get('username', request.user.username).strip() or request.user.username
        request.user.company_name = request.POST.get('company_name', '').strip()
        request.user.save(update_fields=['username', 'company_name'])
        messages.success(request, 'Profile updated.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html')
