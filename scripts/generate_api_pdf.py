"""Generate Lively_API_Reference.pdf — one-off doc script."""

from fpdf import FPDF


class Doc(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def main() -> None:
    pdf = Doc()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_left_margin(16)
    pdf.set_right_margin(16)
    pdf.set_x(16)

    def body(t: str) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5, t)
        pdf.ln(0.5)

    def mono(t: str) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Courier", "", 7.5)
        pdf.set_text_color(25, 25, 25)
        pdf.set_fill_color(245, 245, 245)
        usable = pdf.epw
        pdf.multi_cell(usable, 4.0, t, fill=True)
        pdf.set_x(pdf.l_margin)
        pdf.ln(1.5)

    def h1(t: str) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(0, 9, t)
        pdf.ln(2)

    def h2(t: str) -> None:
        pdf.ln(3)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(0, 7, t)
        pdf.ln(1)

    def h3(t: str) -> None:
        pdf.ln(1)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, t)

    h1("Lively Backend API Reference")
    body("Base URL prefix: /api/v1")
    body("JSON uses camelCase. Auth: Authorization: Bearer <jwt> where noted.")
    body("Interactive Swagger: GET /docs")

    h2("1. Plans")
    body("GET /api/v1/plans  (public, no auth)")
    body("Returns monthly and yearly subscription plan catalog.")
    h3("Response 200")
    mono(
        "{\n"
        '  "success": true,\n'
        '  "plans": [\n'
        "    {\n"
        '      "id": "monthly", "name": "Monthly", "price": 15.99,\n'
        '      "billingInterval": "month", "maxParents": 1, "maxChildren": 6\n'
        "    },\n"
        "    {\n"
        '      "id": "yearly", "name": "Yearly", "price": 149.49,\n'
        '      "billingInterval": "year", "maxParents": 1, "maxChildren": 6\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    h2("2. Auth - Invite code and login subscription")
    body(
        "Invite codes are 6 chars from 23456789ABCDEFGHJKMNPQRSTUVWXYZ "
        "(no 0/O/1/I/L), unique per guardian. Generated on email verify."
    )

    h3("POST /api/v1/auth/email/verify")
    body("Verifies email, creates invite code, returns JWT.")
    mono(
        'Request: { "email": "parent@example.com", "code": "4821" }\n\n'
        "Response 200:\n"
        "{\n"
        '  "success": true,\n'
        '  "message": "Email verified successfully",\n'
        '  "code": "4821",\n'
        '  "token": "<jwt>",\n'
        '  "user": {\n'
        '    "id": "<uuid>", "name": "John Doe",\n'
        '    "email": "parent@example.com", "guardian": true,\n'
        '    "emailVerified": true, "inviteCode": "A3K7MX"\n'
        "  },\n"
        '  "children": []\n'
        "}"
    )

    h3("POST /api/v1/auth/login")
    body("Returns inviteCode on user and subscription (null until billing exists).")
    mono(
        'Request: { "email": "parent@example.com", "password": "Demo@123" }\n\n'
        "Response 200:\n"
        "{\n"
        '  "success": true, "message": "Login successful", "token": "<jwt>",\n'
        '  "user": { "inviteCode": "A3K7MX", "...": "..." },\n'
        '  "children": [], "subscription": null\n'
        "}"
    )

    h3("POST /api/v1/auth/invite-code/regenerate  (auth required)")
    body("No body. Replaces family invite code.")
    mono(
        "Headers: Authorization: Bearer <jwt>\n\n"
        "Response 200:\n"
        "{\n"
        '  "success": true,\n'
        '  "message": "Invite code regenerated",\n'
        '  "inviteCode": "B9H2NP"\n'
        "}"
    )

    h2("3. Promo code validate")
    body("POST /api/v1/promo-code/validate  (auth required)")
    body(
        "Validates active, unexpired codes under redemption limits. "
        "Does not redeem. Seeded sample: LIVELY20 (20% off)."
    )
    mono(
        'Request: { "code": "LIVELY20" }\n\n'
        "Valid 200:\n"
        "{\n"
        '  "success": true, "valid": true, "code": "LIVELY20",\n'
        '  "discountPercent": 20, "message": "Promo code applied"\n'
        "}\n\n"
        "Invalid 200:\n"
        "{\n"
        '  "success": true, "valid": false, "code": "BADCODE",\n'
        '  "discountPercent": null,\n'
        '  "message": "Invalid or expired promo code"\n'
        "}\n\n"
        "Errors: 401 Unauthorized"
    )

    h2("4. Children CRUD")
    body(
        "All routes require Bearer JWT. Child ids are UUIDs. Soft delete. "
        "Max 6 active children per parent. PIN stored hashed; create echoes plain PIN."
    )

    h3("POST /api/v1/children")
    mono(
        "Request:\n"
        "{\n"
        '  "name": "Alex", "dateOfBirth": "2015-06-20", "gender": "boy",\n'
        '  "devices": ["this_device", "shared_device"], "pin": "6756"\n'
        "}\n\n"
        "Response 201:\n"
        "{\n"
        '  "success": true, "message": "Child created successfully",\n'
        '  "child": {\n'
        '    "id": "<uuid>", "name": "Alex",\n'
        '    "dateOfBirth": "2015-06-20", "gender": "boy",\n'
        '    "devices": ["this_device", "shared_device"],\n'
        '    "pin": "6756", "onBoarding": false\n'
        "  }\n"
        "}"
    )

    h3("GET /api/v1/children")
    mono(
        "With children:\n"
        "{\n"
        '  "success": true, "message": "Children fetched successfully",\n'
        '  "children": [{ "id": "<uuid>", "name": "Alex", ... }]\n'
        "}\n\n"
        "Empty:\n"
        '{ "success": true, "message": "No children found", "children": [] }'
    )

    h3("GET /api/v1/children/{childId}")
    mono(
        "Response 200:\n"
        "{\n"
        '  "success": true, "message": "Child fetched successfully",\n'
        '  "child": {\n'
        '    "id": "<uuid>", "name": "Alex",\n'
        '    "dateOfBirth": "2015-06-20", "gender": "boy",\n'
        '    "devices": ["this_device", "shared_device"],\n'
        '    "onBoarding": false,\n'
        '    "progress": { "completedActivities": 0, "currentLevel": null }\n'
        "  }\n"
        "}"
    )

    h3("PATCH /api/v1/children/{childId}")
    body("Partial update. All fields optional. Response omits pin.")
    mono(
        "Request example:\n"
        '{ "name": "Alex", "dateOfBirth": "2015-06-20", "gender": "boy",\n'
        '  "devices": ["this_device"], "pin": "6756" }\n\n'
        "Response 200: success + updated child (no pin field)"
    )

    h3("DELETE /api/v1/children/{childId}")
    body("Soft delete. Subsequent get returns 404.")
    mono(
        "Response 200:\n"
        "{\n"
        '  "success": true,\n'
        '  "message": "Child removed successfully",\n'
        '  "childId": "<uuid>"\n'
        "}"
    )

    h3("Children error responses")
    mono(
        "400 Invalid child id / validation / max children\n"
        "401 Unauthorized\n"
        "404 Child not found"
    )

    h2("5. Related endpoints")
    body("POST /api/v1/auth/signup")
    body("POST /api/v1/auth/email/resend")
    body("GET /health")

    out = r"d:\Lively\Lively_API_Reference.pdf"
    pdf.output(out)
    print(out)


if __name__ == "__main__":
    main()
