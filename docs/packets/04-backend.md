# 4/11 Backend

`POST /authorizations` stops at the amount ceiling, then at card length, then at the decline plate, then at the approval card. Any other valid card uses the stored institution sentence, or says there is no decline rule. The HTTP response of the POST is 200. The decision status is the `http_status` field. The full card number is not a response field.
