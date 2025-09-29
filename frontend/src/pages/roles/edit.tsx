import React from "react";
import {
  Edit,
  Form,
  Input,
  useForm,
} from "@refinedev/mui";

export const RoleEdit = () => {
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
          name="description"
          label="Description"
        />
      </Form>
    </Edit>
  );
};