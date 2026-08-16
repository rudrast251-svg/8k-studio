import io
import math
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw, ImageFilter

from billing.models import Plan
from siteeditor.models import SiteConfig
from studio.ai.video_codec import open_writer
from studio.models import Asset


def _make_demo_photo() -> bytes:
    """A soft, slightly-blurred low-res-style gradient portrait scene, used as
    a realistic 'before' sample for the enhancement demo."""
    w, h = 960, 600
    img = Image.new('RGB', (w, h))
    top = np.array([28, 18, 54])
    bottom = np.array([10, 8, 22])
    grad = np.linspace(0, 1, h)[:, None]
    row = (top * (1 - grad) + bottom * grad).astype(np.uint8)
    arr = np.repeat(row[:, None, :], w, axis=1)
    img = Image.fromarray(arr, 'RGB')
    draw = ImageDraw.Draw(img)
    rng = np.random.default_rng(7)
    for _ in range(4):
        cx, cy, r = rng.integers(0, w), rng.integers(0, h), rng.integers(120, 260)
        color = tuple(int(c) for c in rng.integers(80, 220, size=3))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    img = img.filter(ImageFilter.GaussianBlur(6))
    img = img.filter(ImageFilter.GaussianBlur(2))
    noise = (rng.normal(0, 9, (h, w, 3))).astype(np.int16)
    noisy = np.clip(np.array(img).astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(noisy, 'RGB')
    small = img.resize((w // 2, h // 2), Image.BILINEAR)
    img = small.resize((w, h), Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=70)
    return buf.getvalue()


def _make_demo_video() -> bytes:
    """A short, real, browser-playable H.264 sample clip of animated shapes,
    used as the default hero video and demo library sample. Returns None if
    no local video codec is available on this host at all (build continues
    without a demo video sample rather than failing)."""
    w, h, fps, seconds = 960, 540, 24, 4
    n = fps * seconds
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'demo.mp4'
        writer, _codec = open_writer(path, fps, (w, h))
        if writer is None:
            return None
        for i in range(n):
            t = i / fps
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            for y in range(h):
                shade = int(10 + 20 * (y / h))
                frame[y, :] = (shade + 10, shade, shade + 25)
            cx = int(w / 2 + math.sin(t * 1.3) * w * 0.25)
            cy = int(h / 2 + math.cos(t * 1.7) * h * 0.2)
            cv2.circle(frame, (cx, cy), 90, (140, 90, 230), -1, lineType=cv2.LINE_AA)
            cv2.circle(frame, (w - cx, h - cy), 60, (230, 140, 90), -1, lineType=cv2.LINE_AA)
            cv2.putText(frame, '8K STUDIO', (int(w * 0.28), int(h * 0.9)), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)
            writer.write(frame)
        writer.release()
        data = path.read_bytes()
        return data if data else None


class Command(BaseCommand):
    help = 'Seed plans, default site configuration, and generated demo sample media.'

    def handle(self, *args, **options):
        self._seed_plans()
        self._seed_demo_assets_and_site()
        self._seed_admin()
        self.stdout.write(self.style.SUCCESS('Seed complete.'))

    @transaction.atomic
    def _seed_plans(self):
        plans = [
            dict(slug='free', name='Free', tagline='Try it out', price_inr=0, monthly_credits=25,
                 max_resolution='4K', order=0, is_featured=False, is_active=False, allows_video=True,
                 features=['25 credits / month', 'Image + video enhancement', 'Up to 4K upscaling', 'Community support']),
            dict(slug='starter', name='Starter', tagline='Photo enhancement', price_inr=49, monthly_credits=100,
                 max_resolution='4K', order=1, is_featured=False, is_active=True, allows_video=False,
                 features=['100 credits / month', 'Photo enhancement only', 'Up to 4K upscaling', 'Email support']),
            dict(slug='pro', name='Full Access', tagline='Photos & videos, up to 8K', price_inr=100, monthly_credits=300,
                 max_resolution='8K', order=2, is_featured=True, is_active=True, allows_video=True,
                 features=['300 credits / month', 'Photo AND video enhancement', 'Up to 8K upscaling', 'Face restoration & background removal', 'Priority processing queue']),
            dict(slug='studio', name='Studio', tagline='For power users & teams', price_inr=199, monthly_credits=700,
                 max_resolution='8K', order=3, is_featured=False, is_active=True, allows_video=True,
                 features=['700 credits / month', 'Photo AND video enhancement', 'Up to 8K upscaling', 'Fastest queue priority', 'Website editor access', 'Priority support']),
        ]
        for data in plans:
            Plan.objects.update_or_create(slug=data['slug'], defaults=data)
        self.stdout.write('Plans seeded.')

    def _seed_demo_assets_and_site(self):
        config = SiteConfig.load()
        if not Asset.objects.filter(is_public_demo=True, kind=Asset.Kind.IMAGE).exists():
            photo_bytes = _make_demo_photo()
            image_asset = Asset(kind=Asset.Kind.IMAGE, source=Asset.Source.DEMO_SAMPLE, is_public_demo=True,
                                 original_name='demo_photo.jpg', label='Demo sample photo', file_size=len(photo_bytes))
            image_asset.file.save('demo_photo.jpg', ContentFile(photo_bytes), save=False)
            image_asset.save()
            with Image.open(io.BytesIO(photo_bytes)) as im:
                image_asset.width, image_asset.height = im.size
            image_asset.save(update_fields=['width', 'height'])
            self.stdout.write('Demo photo generated.')
        else:
            image_asset = Asset.objects.filter(is_public_demo=True, kind=Asset.Kind.IMAGE).first()

        video_asset = Asset.objects.filter(is_public_demo=True, kind=Asset.Kind.VIDEO).first()
        if not video_asset:
            video_bytes = _make_demo_video()
            if video_bytes:
                video_asset = Asset(kind=Asset.Kind.VIDEO, source=Asset.Source.DEMO_SAMPLE, is_public_demo=True,
                                     original_name='demo_clip.mp4', label='Demo sample clip', file_size=len(video_bytes),
                                     width=960, height=540, duration_seconds=4.0)
                video_asset.file.save('demo_clip.mp4', ContentFile(video_bytes), save=False)
                video_asset.save()
                self.stdout.write('Demo video generated.')
            else:
                self.stdout.write(self.style.WARNING(
                    'No local video codec available on this host — skipping demo video sample '
                    '(image demo mode and the site still work fine).'
                ))

        if not config.hero_video and not config.hero_image and video_asset:
            config.hero_video = video_asset

        config.features = config.features or [
            {'icon': '🖼️', 'title': 'Image upscaling to 8K', 'description': 'Sharpen details, reduce noise, restore faces, boost color, and remove backgrounds automatically.'},
            {'icon': '🎬', 'title': 'Video enhancement', 'description': 'Upscale up to 8K, stabilize shaky footage, smooth motion, improve lighting, and manage audio.'},
            {'icon': '💬', 'title': 'Plain-English instructions', 'description': '"Make this brighter and cinematic" — our AI turns your words into a real processing pipeline.'},
            {'icon': '⚡', 'title': 'Background job queue', 'description': "Long video jobs run in the background. You're notified the moment they're done."},
            {'icon': '🎨', 'title': 'AI website editor', 'description': 'Type "change colors to black and gold" and watch this very page update live.'},
            {'icon': '📁', 'title': 'Reusable asset library', 'description': 'Every upload and enhanced result is saved so you can reuse it anywhere on your site.'},
        ]
        config.faqs = config.faqs or [
            {'question': 'Is the 8K upscaling real AI, or just a browser filter?', 'answer': "It's a real external GPU AI provider (Replicate). If no API key is configured yet, the platform runs in a clearly-labeled demo mode using genuine local processing instead of pretending."},
            {'question': 'What file types are supported?', 'answer': 'Images: JPG, PNG, WEBP. Videos: MP4, MOV, WEBM.'},
            {'question': 'How do credits work?', 'answer': 'Every plan includes monthly credits. Each job costs credits based on target resolution and requested operations, deducted when you submit and refunded automatically if a job fails.'},
            {'question': 'Can I edit this website without touching code?', 'answer': 'Yes — signed-in admins can use the Site Editor to type commands like "change colors to black and gold" and see the homepage update live.'},
        ]
        config.save()
        self.stdout.write('Site configuration seeded.')

    def _seed_admin(self):
        from accounts.models import User
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')
        if not email or not password:
            return
        if User.objects.filter(email=email).exists():
            return
        User.objects.create_superuser(username=email.split('@')[0], email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Superuser {email} created.'))
