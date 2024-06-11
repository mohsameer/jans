---
tags:
  - administration
  - auth-server
  - openidc
  - feature
  - claims
  - built-in-claims
---

!!! Note
    Janssen Server uses the terms `claims`, `user claims`, and `attributes`
    interchangeably. They have the same meaning.

# User Claims

A claim is a piece of information asserted about an Entity. User claims refer to
pieces of information about the authenticated user, such as their name,
email address, date of birth, and more. These claims provide the RP with
specific attributes or characteristics associated with the user. The claims
are issued by the IDP after successful authentication and are included in the
ID Token (which is a JSON Web Token (JWT) that contains user-related
information) and are also available through the `/userinfo` endpoint.

## Types of User Claims

### Standard Claims

The Janssen Server includes all standard claims defined
in [OpenID Connect specifications](https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims) as built-in claims.
These claims are pre-defined and available for use after installation.

The built-in user claims in the Janssen Server are listed in the table below:

| Display Name                          | Claim Name                               | Description                                                                                                                                                                              |
|---------------------------------------|------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Username                              | user_name                                | Username of user                                                                                                                                                                         | 
| Password                              | user_password                            | Password of user                                                                                                                                                                         |
| First Name                            | given_name                               | First name of user                                                                                                                                                                       |
| Middle Name                           | middle_name                              | Middle name of user                                                                                                                                                                      |
| Last Name                             | family_name                              | Last name of user                                                                                                                                                                        |
| Display Name                          | name                                     | Display name of user                                                                                                                                                                     |
| Email                                 | email                                    | Email address of user                                                                                                                                                                    |
| Nickname                              | nickname                                 | Nickname used for user                                                                                                                                                                   |
| CIBA Device Registration Token        | jans_backchannel_device_registration_tkn | CIBA Device Registration Token                                                                                                                                                           |
| CIBA User code                        | jans_backchannel_usr_code                | CIBA User code                                                                                                                                                                           |
| Locale                                | locale                                   | End-User's locale, represented as a BCP47 (RFC5646) language tag                                                                                                                         |      
| Website URL                           | website                                  | URL of the End-User's Web page or blog                                                                                                                                                   | 
| IMAP Data                             | imap_data                                | IMAP data                                                                                                                                                                                |   
| jansAdminUIRole                       | jansAdminUIRole                          | Gluu Flex Admin UI role                                                                                                                                                                  |
| Enrollment code                       | jans_enrollment_code                     | Enrollment code                                                                                                                                                                          |
| User Permission                       | user_permission                          | User permission                                                                                                                                                                          |
| Preferred Language                    | preferred_language                       | Preferred language                                                                                                                                                                       |
| Profile URL                           | profile                                  | Profile URL                                                                                                                                                                              |
| Secret Question                       | secret_question                          | Secret question used to verify user identity                                                                                                                                             |
| Email Verified                        | email_verified                           | Is user's email verified?                                                                                                                                                                |
| Birthdate                             | birthdate                                | Baithdate of user                                                                                                                                                                        |   
| Time zone info                        | zoneinfo                                 | The End-User's time zone                                                                                                                                                                 |
| Phone Number verified                 | phone_number_verified                    | Is user's phone number verified?                                                                                                                                                         |
| Preferred Username                    | preferred_username                       | A domain issued and managed identifier for the person                                                                                                                                    |
| TransientId                           | transient_id                             | ...                                                                                                                                                                                      | 
| PersistentId                          | persistent_id                            | ...                                                                                                                                                                                      |
| Country                               | country                                  | User's country                                                                                                                                                                           |     
| Secret Answer                         | secret_answer                            | Secret answer used to verify user identity                                                                                                                                               |
| OpenID Connect JSON formatted address | address                                  | End-User's preferred postal address. The value of the address member is a JSON structure containing some or all of the members defined in OpenID Connect 1.0 Core Standard Section 5.1.1 |
| User certificate                      | user_certificate                         | User certificate                                                                                                                                                                         |
| Organization                          | o                                        | Organization                                                                                                                                                                             |
| Picture URL                           | picture                                  | User's picture url                                                                                                                                                                       | 


### Custom Claims

In addition to standard claims, custom claims are also allowed to be defined
by the IDP. These claims provide flexibility to include application-specific
user attributes that are not covered by the standard claims. Custom claims
can provide additional context or information needed by the RP.

## Inactive Claims

Each claim in the Janssen Server has an active or inactive state. An administrator can
change the claim status to `inactive` to stop the Janssen Server from using that
claim.

The response from OpenId Well-known endpoint 
`https://<jans-host-name>/jans-auth/.well-known/openid-configuration` will only
list claims in `active` status. To see the full list of claims with `active` and
`inactive` status, use the TUI configuration tools as mentioned in 
[Configuring Claims](#configuring-claims) section.

## Configuring User Claims

Refer the [configuration guide](../../config-guide/attribute-configuration.md)
for instructions about how to configure claims/attributes.

## Subject Identifier by Auth Server

The Janssen Server attaches a subject identifier with each end-user entity that
is subject to authentication. This identifier may be received as part of 
the response from the server in certain cases. In the response, this identifier 
is represented by the `sub` claim. To know more refer to the 
[subject identifier](subject-identifiers.md).
