from models import Customer


class CustomerDTO:
    """Traduz o modelo Customer do banco para o dicionário JSON retornado pela API."""

    @staticmethod
    def obj_to_dict(customer: Customer) -> dict:
        return {
            "customer_key": customer.customer_key,
            "status": customer.status.enumerator if customer.status else None,
            "name": customer.name,
            "legal_name": customer.legal_name,
            "email": customer.email,
            "cpf": customer.cpf,
            "cnpj": customer.cnpj,
            "birthdate": customer.birthdate.isoformat() if customer.birthdate else None,
            "phone": customer.phone,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
        }
