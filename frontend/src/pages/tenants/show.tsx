import React from "react";
import {
  Show,
  TextField,
  BooleanField,
  DateField,
} from "@refinedev/mui";

export const TenantShow = () => {
  return (
    <Show>
      <TextField source="id" label="ID" />
      <TextField source="name" label="Name" />
      <TextField source="domain" label="Domain" />
      <TextField source="subscription_tier" label="Subscription Tier" />
      <BooleanField source="is_active" label="Active" />
      <DateField source="created_at" label="Created At" />
      <DateField source="updated_at" label="Updated At" />
      <DateField source="expires_at" label="Expires At" />
    </Show>
  );
};