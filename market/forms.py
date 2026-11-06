import uuid
from decimal import Decimal
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from PIL import Image
from .models import Product, Profile, ProductReport, CATEGORIES, CAMPUSES

class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'campus', 'default_contact', 'is_public']
        widgets = {'bio': forms.Textarea(attrs={'rows': 3})}
        help_texts = {'default_contact': '仅本人在账号设置中可见。发布商品时会预填，可修改或清空；商品联系方式会在审核通过、在售时公开显示。保存默认联系方式不会修改已发布商品。', 'is_public': '开启后，其他人能查看简介、校区和审核通过的商品历史；默认联系方式不会显示在个人主页。', 'campus': '校区会显示在商品详情，即使个人主页未公开。'}

class SearchForm(forms.Form):
    q = forms.CharField(label='关键词', max_length=100, required=False, widget=forms.TextInput(attrs={'placeholder': '搜索标题或描述…'}))
    category = forms.ChoiceField(label='商品类别', choices=[('', '全部类别'), *CATEGORIES], required=False)
    campus = forms.ChoiceField(label='商品所在校区', choices=[('', '全部校区'), *CAMPUSES], required=False)
    min_price = forms.DecimalField(label='最低价格', min_value=0, max_digits=8, decimal_places=2, required=False)
    max_price = forms.DecimalField(label='最高价格', min_value=0, max_digits=8, decimal_places=2, required=False)
    start_date = forms.DateField(label='发布开始日期', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(label='发布结束日期', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    sort = forms.ChoiceField(label='排序方式', required=False, choices=[('newest', '最新发布'), ('oldest', '最早发布'), ('price_asc', '价格从低到高'), ('price_desc', '价格从高到低')], initial='newest')
    def clean(self):
        data = super().clean()
        if data.get('min_price') is not None and data.get('max_price') is not None and data['min_price'] > data['max_price']:
            raise forms.ValidationError('最低价格不能高于最高价格。')
        if data.get('start_date') and data.get('end_date') and data['start_date'] > data['end_date']:
            raise forms.ValidationError('发布开始日期不能晚于结束日期。')
        return data

class ReportForm(forms.ModelForm):
    class Meta:
        model = ProductReport
        fields = ['reason', 'details']
        widgets = {'details': forms.Textarea(attrs={'rows': 5, 'placeholder': '请说明具体问题，避免填写无关个人隐私信息。'})}

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'description', 'price', 'category', 'contact', 'image']
        help_texts = {'image': '可选，JPEG、PNG 或 WebP，最大 3 MB。'}
        widgets = {'description': forms.Textarea(attrs={'rows': 5, 'placeholder': '描述品牌、成色、使用情况和转让原因…'}), 'title': forms.TextInput(attrs={'placeholder': '例如：九成新高等数学教材'}), 'contact': forms.TextInput(attrs={'placeholder': '例如：微信 campus_demo（会公开显示）'}), 'image': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})}
    def clean_price(self):
        value = self.cleaned_data['price']
        if value <= 0: raise forms.ValidationError('价格必须大于 0 元。')
        return value
    def clean_image(self):
        f = self.cleaned_data.get('image')
        if not f: return f
        if not isinstance(f, UploadedFile): return f
        if f.size > settings.PRODUCT_IMAGE_MAX_BYTES: raise forms.ValidationError('图片不能超过 3 MB。')
        try:
            image = Image.open(f)
            fmt = image.format
            if fmt not in {'JPEG', 'PNG', 'WEBP'}: raise ValueError()
            if image.width * image.height > 20_000_000: raise ValueError()
            image.verify()
            f.seek(0)
        except Exception:
            raise forms.ValidationError('请上传有效的 JPEG、PNG 或 WebP 图片（不超过 2000 万像素）。')
        f.name = uuid.uuid4().hex + {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}[fmt]
        return f
