from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from studio.models import Asset
from .ai import parse_site_command, wants_hero_image, wants_hero_video
from .models import EditCommand, SiteConfig


@staff_member_required
def editor(request):
    config = SiteConfig.load()

    if request.method == 'POST':
        instruction = request.POST.get('instruction', '').strip()
        asset_id = request.POST.get('asset_id')
        patch = {}
        error = ''
        if not instruction and not asset_id:
            error = 'Type a command or pick an asset to apply.'
        else:
            try:
                patch = parse_site_command(instruction) if instruction else {}
                if asset_id:
                    asset = get_object_or_404(Asset, pk=asset_id)
                    if wants_hero_video(instruction) or asset.kind == Asset.Kind.VIDEO:
                        config.hero_video = asset
                        patch['hero_video'] = asset.pk
                    elif wants_hero_image(instruction) or asset.kind == Asset.Kind.IMAGE:
                        config.hero_image = asset
                        patch['hero_image'] = asset.pk

                for field, value in patch.items():
                    if field in ('hero_video', 'hero_image'):
                        continue
                    setattr(config, field, value)
                config.updated_by = request.user
                config.save()
                if not patch:
                    error = "I couldn't find anything to change from that instruction. Try mentioning a color, headline text in quotes, autoplay/mute, or pick an asset for the hero."
            except Exception as exc:
                error = str(exc)

        EditCommand.objects.create(
            user=request.user, instruction=instruction or f'[applied asset #{asset_id}]',
            patch_applied=patch, success=not error, error_message=error,
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, 'Live preview updated. Changes are already visible on the homepage.')
        return redirect('siteeditor:editor')

    history = EditCommand.objects.filter(user=request.user)[:15]
    assets = Asset.objects.filter(owner=request.user).exclude(source=Asset.Source.ENHANCED) | Asset.objects.filter(is_public_demo=True)
    return render(request, 'siteeditor/editor.html', {
        'config': config,
        'history': history,
        'assets': assets.distinct()[:24],
    })


@staff_member_required
def reset(request):
    if request.method == 'POST':
        SiteConfig.objects.filter(pk=1).delete()
        SiteConfig.load()
        messages.success(request, 'Site reset to defaults.')
    return redirect('siteeditor:editor')
