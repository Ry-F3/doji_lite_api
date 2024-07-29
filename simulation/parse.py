from decimal import Decimal, InvalidOperation, Context, ROUND_HALF_EVEN
import re


def parse_decimal(value, threshold=1e-10):
    """
    Parses a string into a Decimal, treating values close to zero as zero.

    Parameters:
        value (str): The string to parse.
        threshold (float): The threshold below which values are considered as zero.

    Returns:
        Decimal: The parsed decimal value, or Decimal('0') if the value is below the threshold.
    """
    try:
        if value.strip() == '--':
            return Decimal('0')
        # Remove any non-numeric characters except for decimal point and minus sign
        cleaned_value = re.sub(r'[^\d.,-]', '', value)
        # Convert cleaned value to Decimal
        if cleaned_value:
            decimal_value = Decimal(cleaned_value.replace(',', ''))
            # Treat very small values as zero
            if abs(decimal_value) < threshold:
                return Decimal('0')
            return decimal_value
        return Decimal('0')
    except (IndexError, ValueError, InvalidOperation):
        return Decimal('0')


price_str = '0E-10'
price = parse_decimal(price_str)
print(price)  # This should print 0
