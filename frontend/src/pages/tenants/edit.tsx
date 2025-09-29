import React from "react";
import {
  Edit,
  Form,
  Input,
  BooleanInput,
  useForm,
} from "@refinedev/mui";

export const TenantEdit = () => {
  const { formLoading, onFinish } = useForm();

  return (
    <Edit isLoading={formLoading}>
      <Form onFinish={onFinish}>
        <Input
          name="name"
          label="Name"
          rules={[{ required: true }]}
        />
        <Input
          name="domain"
          label="Domain"
          rules={[{ required: true }]}
        />
        <Input
          name="subscription_tier"
          label="Subscription Tier"
        />
        <BooleanInput
          name="is_active"
          label="Active"
        />
      </Form>
    </Edit>
  );
};