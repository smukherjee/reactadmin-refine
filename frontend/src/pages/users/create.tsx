import React from "react";
import {
  Create,
  Form,
  Input,
  EmailInput,
  useForm,
} from "@refinedev/mui";

export const UserCreate = () => {
  const { formLoading, onFinish } = useForm();

  const handleSubmit = (values: any) => {
    onFinish({
      ...values,
      client_id: "default-tenant-id", // TODO: Get from context
    });
  };

  return (
    <Create isLoading={formLoading}>
      <Form onFinish={handleSubmit}>
        <EmailInput
          name="email"
          label="Email"
          rules={[{ required: true, type: "email" }]}
        />
        <Input
          name="password"
          label="Password"
          type="password"
          rules={[{ required: true }]}
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
      </Form>
    </Create>
  );
};