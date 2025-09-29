import React from "react";
import {
  Show,
  TextField,
  BooleanField,
  DateField,
} from "@refinedev/mui";

export const RoleShow = () => {
  return (
    <Show>
      <TextField source="id" label="ID" />
      <TextField source="name" label="Name" />
      <TextField source="description" label="Description" />
      <TextField source="permissions" label="Permissions" />
      <BooleanField source="is_system" label="System Role" />
      <TextField source="client_id" label="Client ID" />
      <DateField source="created_at" label="Created At" />
      <DateField source="updated_at" label="Updated At" />
    </Show>
  );
};