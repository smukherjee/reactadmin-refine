import React from "react";
import {
  Edit,
  Form,
  Input,
  EmailInput,
  BooleanInput,
  useForm,
} from "@refinedev/mui";

export const UserEdit = () => {
  const { formLoading, onFinish } = useForm();

  return (
    <Edit isLoading={formLoading}>
      <Form onFinish={onFinish}>
        <EmailInput
          name="email"
          label="Email"
          rules={[{ required: true, type: "email" }]}
        />
        <Input
          name="first_name"
          label="First Name"
          rules={[{ required: true }]}
        />
        <Input
          name="last_name"
          label="Last Name"
          rules={[{ required: true }]}
        />
        <BooleanInput
          name="is_active"
          label="Active"
        />
        <BooleanInput
          name="is_verified"
          label="Verified"
        />
      </Form>
    </Edit>
  );
};