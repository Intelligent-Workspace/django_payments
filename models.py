from django.db import models

class Bitmap():
    #Methods
    def set_flag(self, bit):
        self.flag = (self.flag | (0x01 << bit))
        return self.flag

    def reset_flag(self, bit):
        self.flag &= ~(0x01 << bit)
        return self.flag

    def is_flag_valid(self, bit):
        flag = (self.flag & (0x01 << bit))
        if flag == 0:
            return False
        else:
            return True

# Create your models here.
class Merchant(models.Model, Bitmap):
    unique_id = models.IntegerField()
    provider = models.CharField(max_length=1000)
    merchant_info = models.JSONField(default=dict)

    flag = models.IntegerField(default=0)
    flag2 = models.IntegerField(default=0)

    def set_is_setup_started(self):
        self.set_flag(1)

    def reset_is_setup_started(self):
        self.reset_flag(1)
    
    def check_is_setup_started(self):
        return self.is_flag_valid(1)
    
    def set_is_setup_finished(self):
        self.set_flag(2)

    def reset_is_setup_finished(self):
        self.reset_flag(2)
    
    def check_is_setup_finished(self):
        return self.is_flag_valid(2)


class Customer(models.Model, Bitmap):
    merchant_id = models.IntegerField(default=0)
    unique_id = models.IntegerField()
    customer_info = models.JSONField(default=dict)

    flag = models.IntegerField(default=0)
    flag2 = models.IntegerField(default=0)

class PaymentMethod(models.Model, Bitmap):
    merchant_id = models.IntegerField(default=0)
    unique_id = models.IntegerField()
    payment_method_info = models.JSONField(default=dict)
    
    flag = models.IntegerField(default=0)
    flag2 = models.IntegerField(default=0)

    def set_is_confirm(self):
        self.set_flag(1)

    def reset_is_confirm(self):
        self.reset_flag(1)

    def check_is_confirm(self):
        return self.is_flag_valid(1)