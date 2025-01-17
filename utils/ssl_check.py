import ssl
import socket
import datetime
from OpenSSL import crypto
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes

def check_ssl_certificate(hostname, port=443):
    """
    Проверка SSL-сертификата с подробной диагностикой
    """
    try:
        # Создаем SSL-контекст
        context = ssl.create_default_context()
        
        # Устанавливаем соединение
        with socket.create_connection((hostname, port)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as secure_sock:
                # Получаем сертификат
                cert = secure_sock.getpeercert(binary_form=True)
                x509_cert = x509.load_der_x509_certificate(cert)
                
                # Анализ сертификата
                return {
                    "subject": x509_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
                    "issuer": x509_cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
                    "version": x509_cert.version.name,
                    "serial_number": x509_cert.serial_number,
                    "not_valid_before": x509_cert.not_valid_before,
                    "not_valid_after": x509_cert.not_valid_after,
                    "days_to_expiration": (x509_cert.not_valid_after - datetime.datetime.now()).days
                }
    except Exception as e:
        return {"error": str(e)}

def main():
    # Пример использования
    result = check_ssl_certificate("telegram.org")
    print("SSL Certificate Details:")
    for key, value in result.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()
