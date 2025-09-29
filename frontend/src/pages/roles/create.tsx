import React from "react";
import {
  Create,
  Form,
  Input,
  useForm,
} from "@refinedev/mui";

export const RoleCreate = () => {
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
          name="description"
          label="Description"
        />
      </Form>
    </Create>
  );
};