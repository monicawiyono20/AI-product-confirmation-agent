SECTIONS = [
    (
        "Coverage",
        """
Product Name: SecureLife Term Insurance
- Sum insured: IDR 500,000,000
- Policy term: 10 years
- Annual premium: IDR 1,200,000/year
        """,
    ),
    (
        "Benefits",
        """
1. Death Benefit: Full sum insured paid to the beneficiary upon the insured's death.
2. Total Permanent Disability: Full sum insured paid if the insured becomes totally and permanently disabled.
3. No medical check-up required for sum insured below IDR 500,000,000.
        """,
    ),
    (
        "Exclusions (What's NOT Covered)",
        """
- Death caused by suicide within the first 2 years of the policy.
- Death caused by participating in illegal activities.
- Pre-existing conditions not disclosed at the time of application.
        """,
    ),
    (
        "Important Terms",
        """
- Free-look period: 14 days from policy received (full refund if cancelled within this period).
- Grace period: 30 days for premium payment after the due date.
- Policy will lapse if premium is not paid within the grace period.
        """,
    ),
    (
        "Claim Process",
        """
1. Notify the insurance company within 30 days of the event.
2. Submit the claim form along with the required supporting documents.
3. Claim will be processed within 14 working days.
        """,
    ),
]

SUPPORTING_DOCS = """
Supporting Documents Required for Claim:
1. Policy Number
2. KTP / Identity Information
3. Form Death Confirmation
4. Supporting medical record
5. Copy of first page of savings book
"""

# Full script (used as fallback reference for Q&A)
PRODUCT_SCRIPT = "\n\n".join(f"=== {title} ===\n{content}" for title, content in SECTIONS)
PRODUCT_SCRIPT += f"\n\n=== Supporting Documents ===\n{SUPPORTING_DOCS}"
