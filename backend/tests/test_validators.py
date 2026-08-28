"""app.validators.email_gueltig_pruefen — reine Logik, direkt getestet
statt nur indirekt über die Router-422-Fälle."""

import pytest

from app.validators import email_gueltig_pruefen


def test_gueltige_email_wird_akzeptiert():
    assert email_gueltig_pruefen("Test@Example.com") == "Test@example.com"


def test_ungueltige_email_wird_abgelehnt():
    with pytest.raises(ValueError, match="Ungültige E-Mail-Adresse"):
        email_gueltig_pruefen("nicht-valide")


def test_reservierte_test_domain_wird_akzeptiert():
    # Diese App seedet Demo-Konten selbst unter .test (RFC 2606), siehe
    # app/seed.py und den Docstring in app/validators.py.
    assert email_gueltig_pruefen("admin@example.test") == "admin@example.test"
