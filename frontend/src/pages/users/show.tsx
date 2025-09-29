import React from "react";
import {
  Show,
  TextField,
  EmailField,
  BooleanField,
  DateField,
} from "@refinedev/mui";

export const UserShow = () => {
  return (
    <Show>
      <TextField source="id" label="ID" />
      <EmailField source="email" label="Email" />
      <TextField source="first_name" label="First Name" />
      <TextField source="last_name" label="Last Name" />
      <BooleanField source="is_active" label="Active" />
      <BooleanField source="is_verified" label="Verified" />
      <DateField source="created_at" label="Created At" />
      <DateField source="updated_at" label="Updated At" />
      <DateField source="last_login" label="Last Login" />
    </Show>
  );
};