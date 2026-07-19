import React, { useState } from 'react';
import Input from '../Input';
import SearchInput from '../SearchInput';
import TextArea from '../TextArea';
import Select from '../Select';
import Checkbox from '../Checkbox';
import Radio from '../Radio';
import Switch from '../Switch';

export const FormsShowcase = () => {
  const [checkboxVal, setCheckboxVal] = useState(false);
  const [switchVal, setSwitchVal] = useState(false);
  const [radioVal, setRadioVal] = useState('one');

  return (
    <div className="showcase-section" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <h3 className="text-h3" style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>Forms & Controls</h3>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <Input
          label="Email Address"
          placeholder="name@example.com"
          helperText="We will never share your email address."
        />
        <Input
          label="Password Field"
          type="password"
          placeholder="••••••••"
          error="Password must contain at least 8 characters."
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <SearchInput placeholder="Filter task pipelines..." />
        <Select
          label="Target Cluster Host"
          options={[
            { value: 'us-east', label: 'US East AWS Region' },
            { value: 'eu-west', label: 'EU West GCP Region' },
            { value: 'ap-south', label: 'AP South Azure Region' }
          ]}
        />
      </div>

      <TextArea label="Pipeline Configuration Metadata" placeholder="JSON metadata block..." rows={4} />

      <div style={{ display: 'flex', gap: '32px', borderTop: '1px dashed var(--border-subtle)', paddingTop: '16px' }}>
        <Checkbox
          label="Enable Chaos Injector"
          checked={checkboxVal}
          onChange={(e) => setCheckboxVal(e.target.checked)}
        />

        <Switch
          label="Central Polling Lock"
          checked={switchVal}
          onChange={(e) => setSwitchVal(e.target.checked)}
        />

        <div style={{ display: 'flex', gap: '16px' }}>
          <Radio
            label="Option Alpha"
            name="showcase-radio"
            checked={radioVal === 'one'}
            onChange={() => setRadioVal('one')}
          />
          <Radio
            label="Option Beta"
            name="showcase-radio"
            checked={radioVal === 'two'}
            onChange={() => setRadioVal('two')}
          />
        </div>
      </div>
    </div>
  );
};
export default FormsShowcase;
