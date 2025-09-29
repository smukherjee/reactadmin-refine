import React from "react";
import {
  Create,
  Form,
  Input,
  useForm,
} from "@refinedev/mui";

export const TenantCreate = () => {
  const { formLoading, onFinish } = useForm();

  return (
    <Create isLoading={formLoading}>
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
      </Form>
    </Create>
  );
};